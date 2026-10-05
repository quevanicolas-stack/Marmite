// Clés d'accès (WebAuthn) : vérification côté serveur, sans dépendance.
// Inscription : clientDataJSON (type, défi, origine) + attestationObject (CBOR : authData avec la clé publique COSE).
// Connexion : signature de authData ‖ SHA-256(clientDataJSON) avec la clé enregistrée (ES256 ou RS256).

export const b64url = buf => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
export const deB64url = s => Uint8Array.from(atob(String(s).replace(/-/g, "+").replace(/_/g, "/") + "===".slice((String(s).length + 3) % 4)), c => c.charCodeAt(0));
const sha256 = async data => new Uint8Array(await crypto.subtle.digest("SHA-256", data));
const egaux = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);

// CBOR : juste ce que WebAuthn utilise (entiers, octets, texte, tableaux, tables, simples)
export function cbor(octets, pos = 0) {
  const lire = () => {
    const tete = octets[pos++], maj = tete >> 5, info = tete & 31;
    let n = info;
    if (info === 24) n = octets[pos++];
    else if (info === 25) { n = (octets[pos] << 8) | octets[pos + 1]; pos += 2; }
    else if (info === 26) { n = ((octets[pos] << 24) >>> 0) + (octets[pos + 1] << 16) + (octets[pos + 2] << 8) + octets[pos + 3]; pos += 4; }
    else if (info === 27) throw new Error("cbor : entier trop grand");
    switch (maj) {
      case 0: return n;
      case 1: return -1 - n;
      case 2: { const v = octets.slice(pos, pos + n); pos += n; return v; }
      case 3: { const v = new TextDecoder().decode(octets.slice(pos, pos + n)); pos += n; return v; }
      case 4: { const v = []; for (let i = 0; i < n; i++) v.push(lire()); return v; }
      case 5: { const v = new Map(); for (let i = 0; i < n; i++) { const k = lire(); v.set(k, lire()); } return v; }
      case 7: return info === 20 ? false : info === 21 ? true : null;
      default: throw new Error("cbor : type non pris en charge");
    }
  };
  const valeur = lire();
  return [valeur, pos];
}

function lireAuthData(ad) {
  const flags = ad[32];
  const res = { rpIdHash: ad.slice(0, 32), presence: !!(flags & 1), verifie: !!(flags & 4), compteur: ((ad[33] << 24) >>> 0) + (ad[34] << 16) + (ad[35] << 8) + ad[36] };
  if (flags & 0x40) {
    const long = (ad[53] << 8) | ad[54];
    res.idCle = ad.slice(55, 55 + long);
    res.cose = cbor(ad, 55 + long)[0];
  }
  return res;
}
// Clé publique COSE → JWK (ES256 : kty 2, alg -7 ; RS256 : kty 3, alg -257)
function coseVersJwk(m) {
  const kty = m.get(1), alg = m.get(3);
  if (kty === 2 && m.get(-1) === 1) return { alg: -7, jwk: { kty: "EC", crv: "P-256", x: b64url(m.get(-2)), y: b64url(m.get(-3)), ext: true } };
  if (kty === 3) return { alg: -257, jwk: { kty: "RSA", n: b64url(m.get(-1)), e: b64url(m.get(-2)), alg: "RS256", ext: true } };
  throw new Error("type de clé non pris en charge (" + kty + "/" + alg + ")");
}
async function verifierClientData(json, type, defi, origine) {
  const c = JSON.parse(new TextDecoder().decode(json));
  if (c.type !== type) throw new Error("type inattendu");
  if (c.challenge !== defi) throw new Error("défi différent");
  if (c.origin !== origine) throw new Error("origine différente : " + c.origin);
}

// Retourne { idCle, cle (JWK), alg, compteur }
export async function verifierInscription(rep, { defi, origine, rpId }) {
  const clientData = deB64url(rep.response.clientDataJSON);
  await verifierClientData(clientData, "webauthn.create", defi, origine);
  const att = cbor(deB64url(rep.response.attestationObject))[0];
  const ad = lireAuthData(att.get("authData"));
  if (!egaux(ad.rpIdHash, await sha256(new TextEncoder().encode(rpId)))) throw new Error("rpId différent");
  if (!ad.presence) throw new Error("présence non confirmée");
  if (!ad.idCle || !ad.cose) throw new Error("clé absente");
  if (b64url(ad.idCle) !== rep.id) throw new Error("identifiant de clé incohérent");
  const { alg, jwk } = coseVersJwk(ad.cose);
  return { idCle: rep.id, cle: jwk, alg, compteur: ad.compteur };
}

// Signature ECDSA DER → brute (r ‖ s), ce qu'attend WebCrypto
function derVersBrut(der) {
  let p = 2;
  const lireEntier = () => { p++; const n = der[p++]; let v = der.slice(p, p + n); p += n; while (v.length > 32 && v[0] === 0) v = v.slice(1); const o = new Uint8Array(32); o.set(v, 32 - v.length); return o; };
  const r = lireEntier(), s = lireEntier(), out = new Uint8Array(64); out.set(r); out.set(s, 32); return out;
}
// Retourne le nouveau compteur
export async function verifierConnexion(rep, { defi, origine, rpId, cle, alg, compteur }) {
  const clientData = deB64url(rep.response.clientDataJSON);
  await verifierClientData(clientData, "webauthn.get", defi, origine);
  const authData = deB64url(rep.response.authenticatorData);
  const ad = lireAuthData(authData);
  if (!egaux(ad.rpIdHash, await sha256(new TextEncoder().encode(rpId)))) throw new Error("rpId différent");
  if (!ad.presence) throw new Error("présence non confirmée");
  const signe = new Uint8Array(authData.length + 32); signe.set(authData); signe.set(await sha256(clientData), authData.length);
  let sig = deB64url(rep.response.signature), ok;
  if (alg === -7) {
    const k = await crypto.subtle.importKey("jwk", cle, { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]);
    ok = await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, k, derVersBrut(sig), signe);
  } else {
    const k = await crypto.subtle.importKey("jwk", cle, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
    ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", k, sig, signe);
  }
  if (!ok) throw new Error("signature invalide");
  // les clés synchronisées (iCloud, Google) renvoient toujours 0 ; sinon le compteur doit avancer
  if (compteur > 0 && ad.compteur !== 0 && ad.compteur <= compteur) throw new Error("compteur de la clé en arrière");
  return ad.compteur;
}
