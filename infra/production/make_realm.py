"""Génère le realm Keycloak de PRODUCTION à partir du realm de développement.

Usage (depuis le dossier XPASS) :
    python infra/production/make_realm.py --domain xpass.fr --smtp-host smtp.exemple.fr --smtp-user ... \
        --smtp-from no-reply@xpass.fr --portals-secret <secret>

- adresses HTTPS app./pro./auth.<domaine> à la place de localhost ;
- secret du client des portails fourni (le même que OIDC_PORTALS_CLIENT_SECRET) ;
- aucun utilisateur ; HTTPS exigé partout ; force brute protégée ; SMTP de production.
Le mot de passe SMTP n'est pas écrit dans le fichier : saisissez-le ensuite dans la console Keycloak
(Realm settings → Email), accessible uniquement par un tunnel SSH (voir docs/DEPLOIEMENT.md).
"""
import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--domain", required=True)
    a.add_argument("--portals-secret", required=True)
    a.add_argument("--smtp-host", required=True)
    a.add_argument("--smtp-port", default="587")
    a.add_argument("--smtp-user", default="")
    a.add_argument("--smtp-from", required=True)
    args = a.parse_args()
    if len(args.portals_secret) < 32:
        raise SystemExit("Le secret des portails doit faire au moins 32 caractères.")

    realm = json.loads((ROOT / "infra/keycloak/xpass-realm.json").read_text(encoding="utf-8"))
    app, pro = f"https://app.{args.domain}", f"https://pro.{args.domain}"
    apex, www = f"https://{args.domain}", f"https://www.{args.domain}"
    admin, rh = f"https://admin.{args.domain}", f"https://rh.{args.domain}"
    realm["users"] = []
    realm["sslRequired"] = "all"
    realm["bruteForceProtected"] = True
    realm["smtpServer"] = {
        "host": args.smtp_host, "port": args.smtp_port, "from": args.smtp_from, "fromDisplayName": "XPASS",
        "starttls": "true", "auth": "true" if args.smtp_user else "false", "user": args.smtp_user,
    }
    for c in realm["clients"]:
        if c["clientId"] == "xpass-mobile":
            c["baseUrl"] = f"{app}/"
            c["redirectUris"] = [f"{app}/*", "xpass://auth/*"]
            c["webOrigins"] = [app]
            c["attributes"]["post.logout.redirect.uris"] = f"{app}/*##xpass://auth/*"
        elif c["clientId"] == "xpass-portals":
            c["baseUrl"] = f"{apex}/"
            c["secret"] = args.portals_secret
            c["redirectUris"] = [
                f"{apex}/auth/callback", f"{www}/auth/callback", f"{pro}/auth/callback",
                f"{admin}/auth/callback", f"{rh}/auth/callback",
            ]
            c["webOrigins"] = [apex, www, pro, admin, rh]
            c["attributes"]["post.logout.redirect.uris"] = (
                f"{apex}/login##{www}/login##{pro}/login##{admin}/login##{rh}/login"
            )
    out = ROOT / "infra/production/keycloak/xpass-realm.prod.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(realm, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Realm de production écrit : {out}")


if __name__ == "__main__":
    main()
