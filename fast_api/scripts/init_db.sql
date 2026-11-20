-- ============================================================
-- 个人知识库（Vue3 + FastAPI + MySQL）初始化脚本
-- 用法（在 fast_api 目录下）：
--   & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p < scripts\init_db.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS kb_db
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

CREATE DATABASE IF NOT EXISTS kb_test
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

-- 专用账号：权限只给到这两个库（最小权限原则）
-- 把 change_me 换成你自己的密码，并同步写进 .env
CREATE USER IF NOT EXISTS 'kb_user'@'localhost' IDENTIFIED BY 'change_me';
CREATE USER IF NOT EXISTS 'kb_user'@'127.0.0.1' IDENTIFIED BY 'change_me';
GRANT ALL PRIVILEGES ON kb_db.*   TO 'kb_user'@'localhost';
GRANT ALL PRIVILEGES ON kb_db.*   TO 'kb_user'@'127.0.0.1';
GRANT ALL PRIVILEGES ON kb_test.* TO 'kb_user'@'localhost';
GRANT ALL PRIVILEGES ON kb_test.* TO 'kb_user'@'127.0.0.1';
FLUSH PRIVILEGES;

USE kb_db;

CREATE TABLE IF NOT EXISTS notes (
  id         BIGINT      NOT NULL AUTO_INCREMENT,
  title      VARCHAR(200) NOT NULL,
  content    MEDIUMTEXT   NOT NULL,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_notes_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS tags (
  id   INT         NOT NULL AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_tags_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS note_tags (
  note_id BIGINT NOT NULL,
  tag_id  INT    NOT NULL,
  PRIMARY KEY (note_id, tag_id),
  KEY idx_nt_tag (tag_id),
  CONSTRAINT fk_nt_note FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
  CONSTRAINT fk_nt_tag  FOREIGN KEY (tag_id)  REFERENCES tags(id)  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
