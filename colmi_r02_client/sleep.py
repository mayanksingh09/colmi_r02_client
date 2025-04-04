from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum
from typing import List

class SleepType(IntEnum):
    NODATA = 0
    ERROR = 1
    LIGHT = 2
    DEEP = 3
    AWAKE = 5

@dataclass
class SleepPeriod:
    type: SleepType
    minutes: int

@dataclass
class SleepDay:
    days_ago: int
    sleep_start: int  # Minutes after midnight
    sleep_end: int    # Minutes after midnight
    sleep_periods: List[SleepPeriod]

@dataclass
class SleepData:
    sleep_days: List[SleepDay]

# Big Data protocol constants
SLEEP_DATA_ID = 39
BIG_DATA_MAGIC = 188
BIG_DATA_SERVICE_UUID = "de5bf728-d711-4e47-af26-65e3012a5dc7"
BIG_DATA_WRITE_CHAR_UUID = "de5bf72a-d711-4e47-af26-65e3012a5dc7"
BIG_DATA_NOTIFY_CHAR_UUID = "de5bf729-d711-4e47-af26-65e3012a5dc7"

def create_sleep_request() -> bytearray:
    """Create a request packet for sleep data"""
    # Following the BigDataRequest structure from the docs
    return bytearray([
        BIG_DATA_MAGIC,  # bigDataMagic
        SLEEP_DATA_ID,   # dataId
        0x00, 0x00,      # dataLen = 0
        0xFF, 0xFF       # crc16 = 0xFFFF
    ])

class SleepDataParser:
    def __init__(self):
        self._buffer = bytearray()
        self._expected_length = 0
        self._parsing_complete = False

    def parse(self, packet: bytearray) -> SleepData | None:
        """Parse a sleep data packet"""
        if len(packet) < 6:  # Minimum header size
            return None

        # Verify magic number and data ID
        if packet[0] != BIG_DATA_MAGIC or packet[1] != SLEEP_DATA_ID:
            return None

        # Get data length from packet
        data_len = (packet[3] << 8) | packet[2]
        
        # If this is the first packet, initialize expected length
        if not self._buffer:
            self._expected_length = data_len + 6  # Add header size

        # Add packet to buffer
        self._buffer.extend(packet)

        # Check if we have received all data
        if len(self._buffer) >= self._expected_length:
            return self._parse_complete_data()

        return None

    def _parse_complete_data(self) -> SleepData:
        """Parse the complete sleep data once all packets are received"""
        data = self._buffer
        sleep_days = []
        
        # Skip header (6 bytes) and get number of days
        pos = 6
        num_days = data[pos]
        pos += 1

        for _ in range(num_days):
            days_ago = data[pos]
            pos += 1
            
            cur_day_bytes = data[pos]
            pos += 1
            
            sleep_start = int.from_bytes(data[pos:pos+2], byteorder='little', signed=True)
            pos += 2
            
            sleep_end = int.from_bytes(data[pos:pos+2], byteorder='little', signed=True)
            pos += 2

            # Parse sleep periods
            sleep_periods = []
            remaining_bytes = cur_day_bytes - 5  # Subtract the bytes we've already read for this day
            while remaining_bytes > 0:
                sleep_type = SleepType(data[pos])
                pos += 1
                minutes = data[pos]
                pos += 1
                sleep_periods.append(SleepPeriod(sleep_type, minutes))
                remaining_bytes -= 2

            sleep_days.append(SleepDay(
                days_ago=days_ago,
                sleep_start=sleep_start,
                sleep_end=sleep_end,
                sleep_periods=sleep_periods
            ))

        # Reset parser state
        self._buffer.clear()
        self._expected_length = 0
        self._parsing_complete = False

        return SleepData(sleep_days=sleep_days) 