"""把某个用户名设为管理员：cd backend && python set_admin.py <username>"""
import sys

from db.database import SessionLocal, init_db
from models.database import User

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法：python set_admin.py <username>")
        sys.exit(1)
    init_db()
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == sys.argv[1]).first()
        if not u:
            print(f"用户 {sys.argv[1]} 不存在")
            sys.exit(1)
        u.is_admin = True
        db.commit()
        print(f"已将 {u.username} 设为管理员")
    finally:
        db.close()
