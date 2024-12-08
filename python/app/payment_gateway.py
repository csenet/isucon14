import time
from collections.abc import Callable
from http import HTTPStatus
import json

import urllib3
from pydantic import BaseModel, ValidationError

from .models import Ride


class UpstreamError(Exception):
    """上流サービスでの予期しないエラーを表す例外クラス。"""
    pass


class PaymentGatewayPostPaymentRequest(BaseModel):
    amount: int


class PaymentGatewayGetPaymentsResponseOne(BaseModel):
    amount: int
    status: str


# PoolManagerの初期化（接続の再利用）
http = urllib3.PoolManager()


def request_payment_gateway_post_payment(
    payment_gateway_url: str,
    token: str,
    param: PaymentGatewayPostPaymentRequest,
    retrieve_rides_order_by_created_at_asc: Callable[[], list[Ride]],
) -> None:
    """
    決済ゲートウェイに支払いリクエストを送信し、必要に応じてリトライを行う。

    Args:
        payment_gateway_url (str): 決済ゲートウェイのベースURL。
        token (str): 認証トークン。
        param (PaymentGatewayPostPaymentRequest): 支払いリクエストパラメータ。
        retrieve_rides_order_by_created_at_asc (Callable[[], list[Ride]]): ライドを取得する関数。

    Raises:
        UpstreamError: 支払いとライドの数が一致しない場合。
        RuntimeError: GET /payments が予期しないステータスコードを返した場合。
        Exception: 最大リトライ回数を超えた場合。
    """
    max_retries = 5
    backoff_factor = 0.1  # 初回の待機時間（秒）

    for attempt in range(max_retries + 1):
        try:
            # POST /payments リクエストの送信
            post_url = f"{payment_gateway_url}/payments"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            }
            encoded_data = json.dumps(param.dict()).encode('utf-8')
            res = http.request(
                "POST",
                post_url,
                body=encoded_data,
                headers=headers,
                timeout=urllib3.Timeout(connect=5.0, read=10.0),
                retries=False,
            )

            if res.status != HTTPStatus.NO_CONTENT:
                # POST が 204 以外の場合、GET で状況を確認
                get_url = f"{payment_gateway_url}/payments"
                get_res = http.request(
                    "GET",
                    get_url,
                    headers={
                        "Authorization": f"Bearer {token}",
                    },
                    timeout=urllib3.Timeout(connect=5.0, read=10.0),
                    retries=False,
                )

                if get_res.status != HTTPStatus.OK:
                    raise RuntimeError(
                        f"[GET /payments] unexpected status code ({get_res.status})"
                    )

                try:
                    payments_data = json.loads(get_res.data.decode('utf-8'))
                except json.JSONDecodeError as e:
                    raise UpstreamError("Failed to decode payments JSON") from e

                try:
                    payments = [
                        PaymentGatewayGetPaymentsResponseOne(**item)
                        for item in payments_data
                    ]
                except ValidationError as e:
                    raise UpstreamError("Invalid payment data from upstream") from e

                rides = retrieve_rides_order_by_created_at_asc()

                if len(rides) != len(payments):
                    raise UpstreamError(
                        f"unexpected number of payments: {len(rides)} != {len(payments)}. errored upstream"
                    )
            # 成功した場合はループを抜ける
            return

        except (urllib3.exceptions.TimeoutError, urllib3.exceptions.NewConnectionError, urllib3.exceptions.MaxRetryError) as e:
            # ネットワーク関連のエラーの場合
            if attempt < max_retries:
                sleep_time = backoff_factor * (2 ** attempt)  # 指数的バックオフ
                time.sleep(sleep_time)
                continue
            else:
                raise

        except (RuntimeError, UpstreamError) as e:
            # アプリケーションレベルのエラーの場合
            if attempt < max_retries:
                sleep_time = backoff_factor * (2 ** attempt)  # 指数的バックオフ
                time.sleep(sleep_time)
                continue
            else:
                raise

        except Exception as e:
            # その他の予期しないエラーの場合
            if attempt < max_retries:
                sleep_time = backoff_factor * (2 ** attempt)  # 指数的バックオフ
                time.sleep(sleep_time)
                continue
            else:
                raise

    # 全てのリトライが失敗した場合
    raise Exception("Failed to process payment after multiple retries.")
