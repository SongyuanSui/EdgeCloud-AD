import time
from datetime import datetime, timezone
from daqhats import mcc134, mcc118, TcTypes
import taos  # TDengine Python client

# ===== TDengine BASIC CONFIGURATION =====
DB_NAME = "data"
TABLE_NAME = "realtime_data"
TD_HOST = "localhost"
TD_USER = "root"
TD_PASS = "taosdata"
TD_PORT = 6030

PUBLISH_INTERVAL = 1.5  # Write once every 1.5 seconds


def connect_tdengine():
    """Connect to TDengine and initialize database/table"""
    conn = taos.connect(
        host=TD_HOST,
        user=TD_USER,
        password=TD_PASS,
        port=TD_PORT,
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    cursor.execute(f"USE {DB_NAME}")

    # Use standard TIMESTAMP field
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            ts TIMESTAMP,
            t_ch0 FLOAT,
            t_ch1 FLOAT,
            t_ch2 FLOAT,
            t_ch3 FLOAT,
            v_ch0 FLOAT
        )
    """)
    return conn, cursor


def connectMCC134(address=0):
    return mcc134(address)


def connectMCC118(address=0):
    return mcc118(address)


def openChannel(board, channel, tc_type):
    try:
        board.tc_type_write(channel, tc_type)
    except Exception as e:
        print("openChannel error:", e)


def convert_c_to_f(celsius):
    return (celsius * 9/5) + 32


def insert_row(cursor, ts_iso, t0, t1, t2, t3, v0):
    """
    ts_iso: UTC time string (RFC3339 format, e.g. "2025-10-31T05:00:04Z")
    """
    sql = f"""
        INSERT INTO {TABLE_NAME} VALUES (
            '{ts_iso}',
            {t0},
            {t1},
            {t2},
            {t3},
            {v0}
        )
    """
    cursor.execute(sql)


def start_sampling():
    conn, cursor = connect_tdengine()

    board0 = connectMCC134(0)
    for ch in range(4):
        openChannel(board0, ch, TcTypes.TYPE_K)
    board2 = connectMCC118(1)

    try:
        while True:
            t0 = convert_c_to_f(board0.t_in_read(0))
            t1 = convert_c_to_f(board0.t_in_read(1))
            t2 = convert_c_to_f(board0.t_in_read(2))
            t3 = convert_c_to_f(board0.t_in_read(3))
            v0 = board2.a_in_read(0)

            # === Write with UTC + RFC3339 formatted timestamp ===
            utc_now = datetime.now(timezone.utc)
            ts_iso = utc_now.isoformat(timespec="seconds").replace("+00:00", "Z")

            print(f"[{ts_iso} UTC] t0={t0:.2f}F, t1={t1:.2f}F, t2={t2:.2f}F, "
                  f"t3={t3:.2f}F, v0={v0:.4f}V")

            insert_row(cursor, ts_iso, t0, t1, t2, t3, v0)
            conn.commit()
            time.sleep(max(PUBLISH_INTERVAL, 1))

    except KeyboardInterrupt:
        print("Stopped by user (Ctrl+C).")
    except Exception as e:
        print("Error:", e)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    # keep running after the edge device is power on
    start_sampling()
