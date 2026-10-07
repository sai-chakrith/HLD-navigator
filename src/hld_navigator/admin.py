import argparse
import os

from .store import Store


def main():
    parser = argparse.ArgumentParser(
        description="Local operator: provision or rotate individual access"
    )
    parser.add_argument("user")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--role", choices=["viewer", "editor", "reviewer"], required=True)
    parser.add_argument(
        "--database", default=os.getenv("HLD_NAVIGATOR_DB", ".data/hld_navigator.db")
    )
    args = parser.parse_args()
    token = Store(args.database).provision(args.user, args.workspace, args.role)
    print("Token returned once; store privately. Earlier tokens for this user are revoked.")
    print(token)


if __name__ == "__main__":
    main()
