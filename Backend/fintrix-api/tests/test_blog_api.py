from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.database import Base, engine, SessionLocal
from backend.blog.routes import router as blog_router
from backend.models import BlogComment, BlogPost


class TestBlogApi:
    @classmethod
    def setup_class(cls):
        Base.metadata.create_all(bind=engine)
        cls.app = FastAPI()
        cls.app.include_router(blog_router, prefix="/api/blog")
        cls.client = TestClient(cls.app)

    @classmethod
    def teardown_class(cls):
        cls.client.close()

    def setup_method(self):
        db = SessionLocal()
        db.query(BlogComment).delete()
        db.query(BlogPost).delete()
        db.commit()
        db.close()

    def test_create_post_then_list(self):
        response = self.client.post(
            "/api/blog/posts",
            json={"author": "Nishank", "title": "Forex basics", "body": "A starter discussion."},
        )
        assert response.status_code == 200
        created = response.json()
        assert created["author"] == "Nishank"
        assert created["title"] == "Forex basics"

        list_response = self.client.get("/api/blog/posts")
        assert list_response.status_code == 200
        payload = list_response.json()
        assert len(payload) == 1
        assert payload[0]["id"] == created["id"]

    def test_add_comment(self):
        created_post = self.client.post(
            "/api/blog/posts",
            json={"author": "Nishank", "title": "Risk controls", "body": "Share controls used."},
        ).json()

        response = self.client.post(
            f"/api/blog/posts/{created_post['id']}/comments",
            json={"author": "Analyst", "body": "Track exposure limits daily."},
        )
        assert response.status_code == 200
        updated = response.json()
        assert len(updated["comments"]) == 1
        assert updated["comments"][0]["author"] == "Analyst"

    def test_validation_errors(self):
        response = self.client.post(
            "/api/blog/posts",
            json={"author": "", "title": "", "body": ""},
        )
        assert response.status_code == 400

        missing_post = self.client.post(
            "/api/blog/posts/999999/comments",
            json={"author": "Someone", "body": "Comment"},
        )
        assert missing_post.status_code == 404
