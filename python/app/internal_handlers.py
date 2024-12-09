from http import HTTPStatus

from fastapi import APIRouter
from sqlalchemy import text

from .models import Chair, Ride
from .sql import engine

router = APIRouter(prefix="/api/internal")


# このAPIをインスタンス内から一定間隔で叩かせることで、椅子とライドをマッチングさせる
@router.get("/matching", status_code=HTTPStatus.NO_CONTENT)
def internal_get_matching() -> None:
    # 最も古い未マッチのライドを1件取得
    with engine.begin() as conn:
        ride_row = conn.execute(
            text(
                "SELECT * FROM rides WHERE chair_id IS NULL ORDER BY created_at LIMIT 1"
            )
        ).fetchone()
        if ride_row is None:
            # マッチング対象となるライドがなければ何もしない
            return
        ride = Ride.model_validate(ride_row)
        pickup_lat = ride.pickup_latitude
        pickup_lon = ride.pickup_longitude

        # 候補となる椅子を複数件取得
        # 一番近い椅子から順に試していく（例として10件取得）
        query = text("""
            SELECT c.*
            FROM chairs c
            INNER JOIN chair_locations cl ON c.id = cl.chair_id
            WHERE c.is_active = TRUE
            ORDER BY (ABS(cl.latitude - :lat) + ABS(cl.longitude - :lon)) ASC
            LIMIT 10
        """)

        chair_rows = conn.execute(query, {"lat": pickup_lat, "lon": pickup_lon}).fetchall()
        if not chair_rows:
            # 利用可能な椅子が全く無ければ何もしない
            return

        matched: Chair | None = None

        # 複数候補からempty条件を満たす最初の椅子を探す
        for chair_row in chair_rows:
            candidate = Chair.model_validate(chair_row)

            # 'empty' 判定
            # chair_sent_atが6回セットされたride(=completed)以外がないかを確認する
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
                    {"chair_id": candidate.id},
                ).scalar()
            )

            if empty:
                matched = candidate
                break

        # 候補が全てemptyでなければマッチングを諦める
        if matched is None:
            # ここで諦めず、ランダムに椅子を探すフォールバック手段も検討可能
            # for _ in range(10):
            #     row = conn.execute(
            #         text(
            #             "SELECT c.* FROM chairs c "
            #             "INNER JOIN (SELECT id FROM chairs WHERE is_active = TRUE ORDER BY RAND() LIMIT 1) tmp ON c.id = tmp.id"
            #         )
            #     ).fetchone()
            #     if row is None:
            #         break
            #     candidate = Chair.model_validate(row)
            #     empty = bool(
            #         conn.execute(
            #             text(
            #                 "SELECT COUNT(*) = 0 FROM ("
            #                 "SELECT COUNT(chair_sent_at) = 6 AS completed "
            #                 "FROM ride_statuses "
            #                 "WHERE ride_id IN (SELECT id FROM rides WHERE chair_id = :chair_id) "
            #                 "GROUP BY ride_id"
            #                 ") is_completed WHERE completed = FALSE"
            #             ),
            #             {"chair_id": candidate.id},
            #         ).scalar()
            #     )
            #     if empty:
            #         matched = candidate
            #         break
            return

        # 条件を満たす椅子が見つかった場合にライドに割り当てる
        conn.execute(
            text("UPDATE rides SET chair_id = :chair_id WHERE id = :id"),
            {"chair_id": matched.id, "id": ride.id},
        )
