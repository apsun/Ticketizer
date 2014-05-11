# -*- coding: utf-8 -*-
#
# This file is part of Ticketizer.
# Copyright (c) 2014 Andrew Sun <youlosethegame@live.com>
#
# Ticketizer is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ticketizer is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ticketizer.  If not, see <http://www.gnu.org/licenses/>.


class TrainType:
    NONE = 0
    K = 1
    T = 2
    Z = 4
    D = 8
    G = 16
    C = 32
    OTHER = 64
    ALL = 127

    REVERSE_ABBREVIATION_LOOKUP = {
        "K": K,
        "T": T,
        "Z": Z,
        "D": D,
        "G": G,
        "C": C,
    }


class TicketType:
    NONE = 0
    OTHER = 1
    NO_SEAT = 2
    HARD_SEAT = 4
    SOFT_SEAT = 8
    HARD_SLEEPER = 16
    SOFT_SLEEPER = 32
    SOFT_SLEEPER_PRO = 64
    SECOND_CLASS = 128
    FIRST_CLASS = 256
    SPECIAL = 512
    BUSINESS = 1024
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

    REVERSE_FULL_NAME_LOOKUP = {
        "其他":     OTHER,
        "无座":     NO_SEAT,
        "硬座":     HARD_SEAT,
        "软座":     SOFT_SEAT,
        "硬卧":     HARD_SLEEPER,
        "软卧":     SOFT_SLEEPER,
        "高级软卧":  SOFT_SLEEPER_PRO,
        "二等座":   SECOND_CLASS,
        "一等座":   FIRST_CLASS,
        "特等座":   SPECIAL,
        "商务座":   BUSINESS
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
        OTHER:            "E",
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
        "E": OTHER,
        "W": NO_SEAT,
        "1": HARD_SEAT,
        "2": SOFT_SEAT,
        "3": HARD_SLEEPER,
        "4": SOFT_SLEEPER,
        "6": SOFT_SLEEPER_PRO,
        "O": SECOND_CLASS,
        "8": SECOND_CLASS,
        "M": FIRST_CLASS,
        "7": FIRST_CLASS,
        "P": SPECIAL,
        "9": BUSINESS
    }

    REVERSE_ID2_LOOKUP = {
        "MIN": OTHER,
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


class TicketStatus:
    NOT_APPLICABLE = 0
    NOT_YET_SOLD = 1
    SOLD_OUT = 2
    NORMAL = 3

    REVERSE_TEXT_LOOKUP = {
        "--": NOT_APPLICABLE,
        "*":  NOT_YET_SOLD,
        "无": SOLD_OUT
    }


class TicketPricing:
    NORMAL = 0
    STUDENT = 1

    SEARCH_LOOKUP = {
        NORMAL: "ADULT",
        STUDENT: "0X00"
    }

    PURCHASE_LOOKUP = {
        NORMAL: "00",
        STUDENT: "0X00"
    }


class IdentificationType:
    SECOND_GEN_ID = "1"
    FIRST_GEN_ID = "2"
    HONGKONG_MACAU = "C"
    TAIWAN = "G"
    PASSPORT = "B"

    TEXT_LOOKUP = {
        SECOND_GEN_ID:  "二代身份证",
        FIRST_GEN_ID:   "一代身份证",
        HONGKONG_MACAU: "港澳通行证",
        TAIWAN:         "台湾通行证",
        PASSPORT:       "护照"
    }

    REVERSE_TEXT_LOOKUP = {
        "二代身份证": SECOND_GEN_ID,
        "一代身份证": FIRST_GEN_ID,
        "港澳通行证": HONGKONG_MACAU,
        "台湾通行证": TAIWAN,
        "护照":      PASSPORT
    }


class PassengerType:
    ADULT = "1"
    CHILD = "2"
    STUDENT = "3"
    DISABLED = "4"

    TEXT_LOOKUP = {
        ADULT:    "成人",
        CHILD:    "儿童",
        STUDENT:  "学生",
        DISABLED: "残疾军人"
    }

    REVERSE_TEXT_LOOKUP = {
        "成人":    ADULT,
        "儿童":    CHILD,
        "学生":    STUDENT,
        "残疾军人": DISABLED
    }


class Gender:
    MALE = "M"
    FEMALE = "F"

    TEXT_LOOKUP = {
        MALE:   "男",
        FEMALE: "女"
    }

    REVERSE_TEXT_LOOKUP = {
        "男": MALE,
        "女": FEMALE
    }