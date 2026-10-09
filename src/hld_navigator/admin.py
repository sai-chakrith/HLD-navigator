import argparse
import os

from .store import Store


def main():
    parser = argparse.ArgumentParser(
        description="Local operator: provision, rotate or revoke individual access"
    )
    parser.add_argument("user")
    parser.add_argument("--workspace")
    parser.add_argument("--role", choices=["viewer", "editor", "reviewer"])
    parser.add_argument("--revoke", action="store_true", help="Invalidate access in all workspaces")
    parser.add_argument(
        "--database", default=os.getenv("HLD_NAVIGATOR_DB", ".data/hld_navigator.db")
    )
    args = parser.parse_args()
    if args.revoke:
        if args.workspace or args.role:
            parser.error("Revocation applies to all workspaces; omit --workspace and --role")
        try:
            Store(args.database).revoke(args.user)
        except KeyError:
            parser.exit(1, "User not found\n")
        print("Access revoked in all workspaces. User identity and history retained.")
        return
    if not args.workspace or not args.role:
        parser.error("Provisioning requires --workspace and --role")
    token = Store(args.database).provision(args.user, args.workspace, args.role)
    print("Token returned once; store privately. Earlier tokens for this user are revoked.")
    print(token)


if __name__ == "__main__":
    main()
