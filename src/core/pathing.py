import requests
from . import common
from . import logger


class AlternativePathFinder:

    def __init__(self):
        # Maximum number of transfers allowed
        # A->D = 0 transfers
        # A->B->D = 1 transfer
        # A->B->C->D = 2 transfers
        self.max_transfers = 0

    @classmethod
    def __get_train_data_query_params(cls, train):
        return common.get_ordered_query_params(
            "train_no", train.id,
            "from_station_telecode", train.departure_station.id,
            "to_station_telecode", train.destination_station.id,
            "depart_date", common.date_to_str(train.departure_time.date()))

    @classmethod
    def get_subpath_stations(cls, train, station_list):
        url = "https://kyfw.12306.cn/otn/czxx/queryByTrainNo?" + cls.__get_train_data_query_params(train)
        response = requests.get(url, verify=False)
        response.raise_for_status()
        json_station_list = common.read_json_data(response)["data"]
        logger.debug("Got station data for train " + train.name, response)
        istart = None
        iend = len(json_station_list)
        for i in range(len(json_station_list)):
            station_json = json_station_list[i]
            is_in_path = station_json["isEnabled"]
            if is_in_path and istart is None:
                istart = i
            elif not is_in_path and istart is not None:
                iend = i
                break
        assert json_station_list[istart]["station_name"] == train.departure_station.name
        assert json_station_list[iend-1]["station_name"] == train.destination_station.name
        sub_station_list = [train.departure_station]
        for i in range(istart+1, iend-1):
            station_name = json_station_list[i]["station_name"]
            sub_station_list.append(station_list.get_by_name(station_name))
        sub_station_list.append(train.destination_station)
        # TODO
        print(train.name)
        for station in sub_station_list:
            print(station.name)

    def __get_subpath_pairs(self, station_path):
        # Returns all paths between the first and last items
        # in the list, in the structure list<list<tuple<,>>> like this:
        # [0] -> list        -- list of sub-path travel nodes
        #    [0] -> tuple
        #       [0] -> start -- starting point of sub-path
        #       [1] -> end   -- ending point of sub-path
        #    [1] -> tuple
        #       [0] -> start
        #       [1] -> end
        #    ....
        # ....
        # Given a list [1, 2, 3, 4], the return value will be:
        # [[(1,4)], [(1,2),(2,4)], [(1,3),(3,4)], [(1,2),(2,3),(3,4)]
        def sublists(x):
            if len(x) == 1:
                return [x]
            # Split list into [0, 1, ..., n-2][n-1] parts,
            # then recurse into the first part
            last = [x.pop()]
            left = sublists(x)
            # Left and right trees are equal so we can just copy the left one
            # Also append the [n-1]th element to each item
            right = [sublist[:] + last for sublist in left]
            return left + right

        def pairs(x):
            return [(x[i], x[i+1]) for i in range(len(x)-1)]

        last_value = [station_path.pop()]
        return [pairs(sub + last_value) for sub in sublists(station_path) if len(sub)-2 <= self.max_transfers]
