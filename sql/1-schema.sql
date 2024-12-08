SET CHARACTER_SET_CLIENT = utf8mb4;
SET CHARACTER_SET_CONNECTION = utf8mb4;

USE isuride;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS coupons;
DROP TABLE IF EXISTS ride_statuses;
DROP TABLE IF EXISTS payment_tokens;
DROP TABLE IF EXISTS rides;
DROP TABLE IF EXISTS chair_locations;
DROP TABLE IF EXISTS chairs;
DROP TABLE IF EXISTS chair_models;
DROP TABLE IF EXISTS owners;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS settings;

SET FOREIGN_KEY_CHECKS = 1;

-- システム設定テーブル
DROP TABLE IF EXISTS settings;
CREATE TABLE settings
(
  name  VARCHAR(30) NOT NULL COMMENT '設定名',
  value TEXT        NOT NULL COMMENT '設定値',
  PRIMARY KEY (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT = 'システム設定テーブル';

-- オーナー情報テーブル
DROP TABLE IF EXISTS owners;
CREATE TABLE owners
(
  id                   BINARY(16)   NOT NULL COMMENT 'オーナーID (ULID/UUIDv7想定)',
  name                 VARCHAR(30)  NOT NULL COMMENT 'オーナー名',
  access_token         VARCHAR(255) NOT NULL COMMENT 'アクセストークン',
  chair_register_token VARCHAR(255) NOT NULL COMMENT '椅子登録トークン',
  created_at           DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '登録日時',
  updated_at           DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新日時',
  PRIMARY KEY (id),
  UNIQUE KEY uk_owners_name (name),
  UNIQUE KEY uk_owners_access_token (access_token),
  UNIQUE KEY uk_owners_chair_register_token (chair_register_token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT = '椅子のオーナー情報テーブル';

-- 椅子モデルテーブル
DROP TABLE IF EXISTS chair_models;
CREATE TABLE chair_models
(
  id         BINARY(16)   NOT NULL COMMENT 'モデルID (ULID/UUIDv7想定)',
  name       VARCHAR(50)  NOT NULL COMMENT '椅子モデル名',
  speed      INT          NOT NULL COMMENT '移動速度',
  created_at DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '登録日時',
  updated_at DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新日時',
  PRIMARY KEY (id),
  UNIQUE KEY uk_chair_models_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT = '椅子モデルテーブル';

-- 椅子情報テーブル (model -> model_id)
DROP TABLE IF EXISTS chairs;
CREATE TABLE chairs
(
  id           BINARY(16)   NOT NULL COMMENT '椅子ID (ULID/UUIDv7想定)',
  owner_id     BINARY(16)   NOT NULL COMMENT 'オーナーID',
  model_id     BINARY(16)   NOT NULL COMMENT '椅子モデルID(chair_models.id参照)',
  name         VARCHAR(30)  NOT NULL COMMENT '椅子の名前',
  is_active    TINYINT(1)   NOT NULL COMMENT '配椅子受付中かどうか',
  access_token VARCHAR(255) NOT NULL COMMENT 'アクセストークン',
  created_at   DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '登録日時',
  updated_at   DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新日時',
  PRIMARY KEY (id),
  KEY idx_owner_id (owner_id),
  KEY idx_model_id (model_id),
  CONSTRAINT fk_chairs_owner_id FOREIGN KEY (owner_id) REFERENCES owners(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_chairs_model_id FOREIGN KEY (model_id) REFERENCES chair_models(id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT = '椅子情報テーブル';

-- 椅子の現在位置情報テーブル
DROP TABLE IF EXISTS chair_locations;
CREATE TABLE chair_locations
(
  id         BINARY(16)    NOT NULL COMMENT '位置ID (ULID/UUIDv7想定)',
  chair_id   BINARY(16)    NOT NULL COMMENT '椅子ID',
  latitude   DECIMAL(10,7) NOT NULL COMMENT '緯度',
  longitude  DECIMAL(10,7) NOT NULL COMMENT '経度',
  created_at DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '登録日時',
  PRIMARY KEY (id),
  KEY idx_chair_id (chair_id),
  CONSTRAINT fk_chair_locations_chair_id FOREIGN KEY (chair_id) REFERENCES chairs(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT = '椅子の現在位置情報テーブル';

-- 利用者情報テーブル
DROP TABLE IF EXISTS users;
CREATE TABLE users
(
  id              BINARY(16)   NOT NULL COMMENT 'ユーザーID (ULID/UUIDv7想定)',
  username        VARCHAR(30)  NOT NULL COMMENT 'ユーザー名',
  firstname       VARCHAR(30)  NOT NULL COMMENT '本名(名前)',
  lastname        VARCHAR(30)  NOT NULL COMMENT '本名(名字)',
  date_of_birth   VARCHAR(30)  NOT NULL COMMENT '生年月日',
  access_token    VARCHAR(255) NOT NULL COMMENT 'アクセストークン',
  invitation_code VARCHAR(30)  NOT NULL COMMENT '招待トークン',
  created_at      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '登録日時',
  updated_at      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新日時',
  PRIMARY KEY (id),
  UNIQUE KEY uk_users_username (username),
  UNIQUE KEY uk_users_access_token (access_token),
  UNIQUE KEY uk_users_invitation_code (invitation_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT = '利用者情報テーブル';

-- 決済トークンテーブル
DROP TABLE IF EXISTS payment_tokens;
CREATE TABLE payment_tokens
(
  user_id    BINARY(16)   NOT NULL COMMENT 'ユーザーID',
  token      VARCHAR(255) NOT NULL COMMENT '決済トークン',
  created_at DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '登録日時',
  PRIMARY KEY (user_id),
  CONSTRAINT fk_payment_tokens_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT = '決済トークンテーブル';

-- ライド情報テーブル
DROP TABLE IF EXISTS rides;
CREATE TABLE rides
(
  id                    BINARY(16)    NOT NULL COMMENT 'ライドID (ULID/UUIDv7想定)',
  user_id               BINARY(16)    NOT NULL COMMENT 'ユーザーID',
  chair_id              BINARY(16)    NULL COMMENT '割り当てられた椅子ID',
  pickup_latitude       DECIMAL(10,7) NOT NULL COMMENT '配車位置(緯度)',
  pickup_longitude      DECIMAL(10,7) NOT NULL COMMENT '配車位置(経度)',
  destination_latitude  DECIMAL(10,7) NOT NULL COMMENT '目的地(緯度)',
  destination_longitude DECIMAL(10,7) NOT NULL COMMENT '目的地(経度)',
  evaluation            INT           NULL COMMENT '評価',
  created_at            DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '要求日時',
  updated_at            DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '状態更新日時',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  KEY idx_chair_id (chair_id),
  CONSTRAINT fk_rides_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_rides_chair_id FOREIGN KEY (chair_id) REFERENCES chairs(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT = 'ライド情報テーブル';

-- ライドステータス履歴テーブル
DROP TABLE IF EXISTS ride_statuses;
CREATE TABLE ride_statuses
(
  id         BINARY(16)   NOT NULL COMMENT 'ステータス変更ID (ULID/UUIDv7想定)',
  ride_id    BINARY(16)   NOT NULL COMMENT 'ライドID',
  status     ENUM ('MATCHING', 'ENROUTE', 'PICKUP', 'CARRYING', 'ARRIVED', 'COMPLETED') NOT NULL COMMENT '状態',
  created_at DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '状態変更日時',
  app_sent_at     DATETIME(6) NULL COMMENT 'ユーザーへの状態通知日時',
  chair_sent_at   DATETIME(6) NULL COMMENT '椅子への状態通知日時',
  PRIMARY KEY (id),
  KEY idx_ride_id (ride_id),
  CONSTRAINT fk_ride_statuses_ride_id FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT = 'ライドステータスの変更履歴テーブル';

-- クーポンテーブル
DROP TABLE IF EXISTS coupons;
CREATE TABLE coupons
(
  user_id    BINARY(16)   NOT NULL COMMENT '所有しているユーザーのID',
  code       VARCHAR(255) NOT NULL COMMENT 'クーポンコード',
  discount   INT          NOT NULL COMMENT '割引額',
  created_at DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '付与日時',
  used_by    BINARY(16)   NULL COMMENT 'クーポンが適用されたライドのID',
  PRIMARY KEY (user_id, code),
  KEY idx_used_by (used_by),
  CONSTRAINT fk_coupons_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_coupons_used_by FOREIGN KEY (used_by) REFERENCES rides(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT = 'クーポンテーブル';
