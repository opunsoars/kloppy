import logging
from typing import Tuple, Dict

from kloppy.domain import (
    TrackingDataset,
    DatasetFlag,
    AttackingDirection,
    Frame,
    Point,
    Team,
    Orientation,
)
from kloppy.infra.utils import Readable, performance_logging

from .meta_data import load_meta_data, EPTSMetaData
from .reader import read_raw_data

from .. import TrackingDataSerializer

logger = logging.getLogger(__name__)


class EPTSSerializer(TrackingDataSerializer):
    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "meta_data" not in inputs:
            raise ValueError("Please specify a value for 'meta_data'")
        if "raw_data" not in inputs:
            raise ValueError("Please specify a value for 'raw_data'")

    @staticmethod
    def _frame_from_row(row: dict, meta_data: EPTSMetaData) -> Frame:
        timestamp = row["timestamp"]
        if meta_data.periods and row["period_id"]:
            # might want to search for it instead
            period = meta_data.periods[row["period_id"] - 1]
        else:
            period = None

        players_coordinates = {}
        for team in meta_data.teams:
            for player in team.players:
                if f"player_{player.player_id}_x" in row:
                    players_coordinates[player] = Point(
                        x=row[f"player_{player.player_id}_x"],
                        y=row[f"player_{player.player_id}_y"],
                    )

        return Frame(
            frame_id=row["frame_id"],
            timestamp=timestamp,
            ball_owning_team=None,
            ball_state=None,
            period=period,
            players_coordinates=players_coordinates,
            ball_coordinates=Point(x=row["ball_x"], y=row["ball_y"]),
        )

    def deserialize(
        self, inputs: Dict[str, Readable], options: Dict = None
    ) -> TrackingDataset:
        """
        Deserialize EPTS tracking data into a `TrackingDataset`.

        Parameters
        ----------
        inputs : dict
            input `raw_data` should point to a `Readable` object containing
            the 'csv' formatted raw data. input `meta_data` should point to
            the xml metadata data.
        options : dict
            Options for deserialization of the EPTS file. Possible options are
            `sample_rate` (float between 0 and 1) to specify the amount of
            frames that should be loaded, `limit` to specify the max number of
            frames that will be returned.
        Returns
        -------
        dataset : TrackingDataset
        Raises
        ------
        -

        See Also
        --------

        Examples
        --------
        >>> serializer = EPTSSerializer()
        >>> with open("metadata.xml", "rb") as meta, \
        >>>      open("raw.dat", "rb") as raw:
        >>>     dataset = serializer.deserialize(
        >>>         inputs={
        >>>             'meta_data': meta,
        >>>             'raw_data': raw
        >>>         },
        >>>         options={
        >>>             'sample_rate': 1/12
        >>>         }
        >>>     )
        """
        self.__validate_inputs(inputs)

        if not options:
            options = {}

        sample_rate = float(options.get("sample_rate", 1.0))
        limit = int(options.get("limit", 0))

        with performance_logging("Loading metadata", logger=logger):
            meta_data = load_meta_data(inputs["meta_data"])

        with performance_logging("Loading data", logger=logger):
            # assume they are sorted
            frames = [
                self._frame_from_row(row, meta_data)
                for row in read_raw_data(
                    raw_data=inputs["raw_data"],
                    meta_data=meta_data,
                    sensor_ids=[
                        "position"
                    ],  # we don't care about other sensors
                    sample_rate=sample_rate,
                    limit=limit,
                )
            ]

        return TrackingDataset(records=frames, meta_data=meta_data)

    def serialize(self, dataset: TrackingDataset) -> Tuple[str, str]:
        raise NotImplementedError
