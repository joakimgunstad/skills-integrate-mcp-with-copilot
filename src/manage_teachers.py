import json
from getpass import getpass

from app import TEACHERS_FILE, create_teacher_record


def main() -> None:
    username = input("Teacher username: ").strip()
    if not username:
        raise SystemExit("Username cannot be empty.")

    password = getpass("Teacher password: ")
    if not password:
        raise SystemExit("Password cannot be empty.")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")

    try:
        data = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {"teachers": []}
    except json.JSONDecodeError as exc:
        raise SystemExit("Teacher credentials file contains invalid JSON.") from exc

    if not isinstance(data, dict) or not isinstance(data.get("teachers"), list):
        raise SystemExit("Teacher credentials file must contain a teachers list.")
    if any(
        not isinstance(record, dict) or not isinstance(record.get("username"), str)
        for record in data["teachers"]
    ):
        raise SystemExit("Teacher credentials file contains an invalid record.")
    if any(record["username"] == username for record in data["teachers"]):
        raise SystemExit(f"Teacher username {username!r} already exists.")

    data["teachers"].append(create_teacher_record(username, password))
    try:
        TEACHERS_FILE.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise SystemExit(f"Could not write {TEACHERS_FILE}: {exc}") from exc

    print(f"Added teacher {username!r}. Password hashes are stored in {TEACHERS_FILE}.")


if __name__ == "__main__":
    main()
