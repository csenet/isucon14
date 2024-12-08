from http import HTTPStatus

from fastapi import APIRouter
from sqlalchemy import text

from .models import Chair, Ride
from .sql import engine

router = APIRouter(prefix="/api/internal")


# このAPIをインスタンス内から一定間隔で叩かせることで、椅子とライドをマッチングさせる
@router.get("/matching", status_code=HTTPStatus.NO_CONTENT)
def internal_get_matching() -> None:
    # MEMO: 最もマンハッタン距離？が近い椅子を選んでいる
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT * FROM rides WHERE chair_id IS NULL ORDER BY created_at LIMIT 1"
            )
        ).fetchone()
        
        ride = Ride.model_validate(row)

        pickup_lat = ride.pickup_latitude
        pickup_lon = ride.pickup_longitude


        chairs_rows = conn.execute(
                    text(
                        "SELECT c.id, c.owner_id, c.name, c.model, c.is_active, c.access_token, "
                        "c.created_at as c_created_at, c.updated_at as c_updated_at, "
                        "cl.latitude, cl.longitude, "
                        "cm.speed "
                        "FROM chairs c "
                        "INNER JOIN chair_locations cl ON c.id = cl.chair_id "
                        "INNER JOIN chair_models cm ON c.model = cm.name "
                        "WHERE c.is_active = TRUE"
                    )
                ).fetchall()
        if not chairs_rows:
            chairs_rows = conn.execute(
              text(
                  "SELECT * FROM rides WHERE chair_id IS NULL ORDER BY created_at LIMIT 1"
              )
            ).fetchone()
             
            if not chairs_rows:
                return
        
        alpha = 0.5
        closest_and_fastest:Chair = None
        best_score = float('-inf')


        for c_row in chairs_rows:
                # RowからChairを生成
                # カラム名がモデルに合うように、エイリアス指定等が必要かもしれません。
                # ここでは読み出し時に一旦dict化して合わせています。
                chair_data = {
                    "id": c_row["id"],
                    "owner_id": c_row["owner_id"],
                    "name": c_row["name"],
                    "model": c_row["model"],
                    "is_active": c_row["is_active"],
                    "access_token": c_row["access_token"],
                    "created_at": c_row["c_created_at"],
                    "updated_at": c_row["c_updated_at"],
                }

                chair_obj = Chair.model_validate(chair_data)

                lat = c_row["latitude"]
                lon = c_row["longitude"]
                speed = c_row["speed"]

                distance = abs(lat - pickup_lat) + abs(lon - pickup_lon)
                score = speed - alpha * distance

                if score > best_score:
                    best_score = score
                    closest_and_fastest = chair_obj
        if closest_and_fastest is None:
            return
        
        try:
            empty = bool(
                conn.execute(
                    text(
                        "SELECT COUNT(*) = 0 FROM ("
                        "SELECT COUNT(chair_sent_at) = 6 AS completed "
                        "FROM ride_statuses "
                        "WHERE ride_id IN (SELECT id FROM rides WHERE chair_id = :chair_id) "
                        "GROUP BY ride_id"
                        ") is_completed WHERE completed = FALSE"
                    ),
                    {"chair_id": closest_and_fastest.id},
                ).scalar()
            )
        except Exception as e:
              return
        
        if not empty:
            return
        conn.execute(
                    text("UPDATE rides SET chair_id = :chair_id WHERE id = :id"),
                    {"chair_id": closest_and_fastest.id, "id": ride.id},
                )
             
