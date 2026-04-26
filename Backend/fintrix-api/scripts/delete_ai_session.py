from backend.database import SessionLocal
from backend.ai_agent.models import AISession, AIMessage

def delete_ai_session(session_id: int):
    db = SessionLocal()

    try:
        messages = db.query(AIMessage).filter(
            AIMessage.session_id == session_id
        ).all()

        if not messages:
            print("No messages found")

        deleted_messages = db.query(AIMessage).filter(
            AIMessage.session_id == session_id
        ).delete()

        deleted_session = db.query(AISession).filter(
            AISession.id == session_id
        ).delete()

        db.commit()

        if deleted_session == 0:
            print("Session not found")
        else:
            print(f"Deleted session {session_id}")
            print(f"Messages removed: {deleted_messages}")

    except Exception as e:
        db.rollback()
        print("Error:", e)

    finally:
        db.close()


if __name__ == "__main__":
    try:
        session_id = int(input("Enter AI session ID: "))
        delete_ai_session(session_id)
    except:
        print("Invalid input")