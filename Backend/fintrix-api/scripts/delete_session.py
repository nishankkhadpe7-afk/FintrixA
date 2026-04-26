from backend.database import SessionLocal
from backend.auth.models import WhatIfSession, Message

def delete_session(session_id: int):
    db = SessionLocal()

    try:
        # delete messages first
        deleted_messages = db.query(Message).filter(
            Message.session_id == session_id
        ).delete()

        # delete session
        deleted_session = db.query(WhatIfSession).filter(
            WhatIfSession.id == session_id
        ).delete()

        db.commit()

        print(f"✅ Session {session_id} deleted")
        print(f"🧹 Messages removed: {deleted_messages}")

    except Exception as e:
        db.rollback()
        print("❌ Error:", e)

    finally:
        db.close()


if __name__ == "__main__":
    session_id = input("Enter session ID to delete: ")

    if not session_id.isdigit():
        print("❌ Invalid ID")
    else:
        delete_session(int(session_id))