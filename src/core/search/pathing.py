import requests
from core.processing.containers import ValueRange, ToggleList
from core.processing.filter import TrainFilter
from core import common, logger


class CombinedPath:
    def __init__(self, train_list):
        self.train_list = train_list


class PathFinder:
    def __init__(self, station_list):
        # A list of stations (used for querying the station list)
        self.station_list = station_list

        # TODO: Maybe move the below to a filter object?
        # TODO: Or do we need to filter at each step to
        # TODO: avoid looking through each combination?
        # Maximum number of transfers allowed (-1 is unlimited)
        # A->D = 0 transfers
        # A->B->D = 1 transfer
        # A->B->C->D = 2 transfers
        self.max_transfers = -1
        # The time range (ValueRange<datetime.timedelta>) between successive trains.
        # Set a minimum that is long enough to allow you to get from one
        # train to the other, and a maximum to prevent waiting for too long.
        self.transfer_time_range = ValueRange()
        # A price range for the combined trip (ValueRange<float>)
        self.price_range = ValueRange()
        # A list of stations to avoid
        self.station_blacklist = ToggleList()
        # A filter to apply to each sub-trip
        self.train_filter = TrainFilter()

    @staticmethod
    def __get_train_data_query_params(train):
        return common.get_ordered_query_params(
            "train_no", train.id,
            "from_station_telecode", train.departure_station.id,
            "to_station_telecode", train.destination_station.id,
            "depart_date", common.date_to_str(train.departure_time.date()))

    def __get_substations(self, train):
        url = "https://kyfw.12306.cn/otn/czxx/queryByTrainNo?" + self.__get_train_data_query_params(train)
        response = requests.get(url, verify=False)
        response.raise_for_status()
        json_station_list = common.read_json_data(response)["data"]
        logger.debug("Got station data for train " + train.name, response)
        istart = None
        iend = len(json_station_list)
        for i in range(len(json_station_list)):
            is_in_path = json_station_list[i]["isEnabled"]
            if is_in_path and istart is None:
                istart = i
            elif not is_in_path and istart is not None:
                iend = i
                break
        assert istart is not None
        assert json_station_list[istart]["station_name"] == train.departure_station.name
        assert json_station_list[iend-1]["station_name"] == train.destination_station.name
        sub_station_list = [train.departure_station]
        for i in range(istart+1, iend-1):
            station_name = json_station_list[i]["station_name"]
            sub_station_list.append(self.station_list.get_by_name(station_name))
        sub_station_list.append(train.destination_station)
        return sub_station_list

    def __get_all_paths(self, station_path):
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

        last_value = [station_path.pop()]
        paths = []
        for path in sublists(station_path):
            if self.max_transfers < 0 or len(path)-1 <= self.max_transfers:
                paths.append(path + last_value)
        return paths

    @staticmethod
    def __make_node_pairs(path):
        return [(path[i], path[i+1]) for i in range(len(path)-1)]

    def search(self, train):
        substations = self.__get_substations(train)
        paths = self.__get_all_paths(substations)
        path_pairs = [self.__make_node_pairs(path) for path in paths]
        for path in path_pairs:
            for start, end in path:
                print(start.name, "->", end.name)
            print("--or--")