# -*- coding: utf-8 -*-
class TrainType:
    G = 1       # 高铁
    D = 2       # 动车
    Z = 4       # 直达
    T = 8       # 特快
    K = 16      # 快速
    OTHER = 32  # 其他
    ALL = 63

    FULL_NAME_LOOKUP = {
        G:     "高铁",
        D:     "动车",
        Z:     "直达",
        T:     "特快",
        K:     "快速",
        OTHER: "其他",
    }

    ABBREVIATION_LOOKUP = {
        G: "G",
        D: "D",
        Z: "Z",
        T: "T",
        K: "K",
        OTHER: None
    }

    REVERSE_ABBREVIATION_LOOKUP = {
        "G": G,
        "D": D,
        "Z": Z,
        "T": T,
        "K": K
    }


class TicketType:
    OTHER = 1              # 其他
    NO_SEAT = 2            # 无座
    HARD_SEAT = 4          # 硬座
    SOFT_SEAT = 8          # 软座
    HARD_SLEEPER = 16      # 硬卧
    SOFT_SLEEPER = 32      # 软卧
    SOFT_SLEEPER_PRO = 64  # 高级软卧
    SECOND_CLASS = 128     # 二等座
    FIRST_CLASS = 256      # 一等座
    SPECIAL = 512          # 特等座
    BUSINESS = 1024        # 商务座
    ALL = 2047

    FULL_NAME_LOOKUP = {
        OTHER:            "其他",
        NO_SEAT:          "无座",
        HARD_SEAT:        "硬座",
        SOFT_SEAT:        "软座",
        HARD_SLEEPER:     "硬卧",
        SOFT_SLEEPER:     "软卧",
        SOFT_SLEEPER_PRO: "高级软卧",
        SECOND_CLASS:     "二等座",
        FIRST_CLASS:      "一等座",
        SPECIAL:          "特等座",
        BUSINESS:         "商务座"
    }

    ABBREVIATION_LOOKUP = {
        OTHER:            "qt",
        NO_SEAT:          "wz",
        HARD_SEAT:        "yz",
        SOFT_SEAT:        "rz",
        HARD_SLEEPER:     "yw",
        SOFT_SLEEPER:     "rw",
        SOFT_SLEEPER_PRO: "gr",
        SECOND_CLASS:     "ze",
        FIRST_CLASS:      "zy",
        SPECIAL:          "tz",
        BUSINESS:         "swz"
    }

    REVERSE_ABBREVIATION_LOOKUP = {
        "qt":  OTHER,
        "wz":  NO_SEAT,
        "yz":  HARD_SEAT,
        "rz":  SOFT_SEAT,
        "yw":  HARD_SLEEPER,
        "rw":  SOFT_SLEEPER,
        "gr":  SOFT_SLEEPER_PRO,
        "ze":  SECOND_CLASS,
        "zy":  FIRST_CLASS,
        "tz":  SPECIAL,
        "swz": BUSINESS
    }

    ID_LOOKUP = {
        # OTHER:            "",
        NO_SEAT:          "W",
        HARD_SEAT:        "1",
        SOFT_SEAT:        "2",
        HARD_SLEEPER:     "3",
        SOFT_SLEEPER:     "4",
        SOFT_SLEEPER_PRO: "6",
        SECOND_CLASS:     "O",
        FIRST_CLASS:      "M",
        SPECIAL:          "P",
        BUSINESS:         "9"
    }

    REVERSE_ID_LOOKUP = {
        # "":  OTHER,
        "W": NO_SEAT,
        "1": HARD_SEAT,
        "2": SOFT_SEAT,
        "3": HARD_SLEEPER,
        "4": SOFT_SLEEPER,
        "6": SOFT_SLEEPER_PRO,
        "O": SECOND_CLASS,
        "M": FIRST_CLASS,
        "P": SPECIAL,
        "9": BUSINESS
    }

    REVERSE_ID2_LOOKUP = {
        # "MIN": OTHER,
        "WZ": NO_SEAT,
        "A1": HARD_SEAT,
        "A2": SOFT_SEAT,
        "A3": HARD_SLEEPER,
        "A4": SOFT_SLEEPER,
        "A6": SOFT_SLEEPER_PRO,
        "O":  SECOND_CLASS,
        "M":  FIRST_CLASS,
        "P":  SPECIAL,
        "A9": BUSINESS
    }