import logging
import itertools
from helpers import *
from helpers import Debugger
from configs.config import ALL_CONFIGS, GLOBAL_CONFIG
from amplitude_matrix import AmplitudeMatrix
from window import Window
from configs.debugging_config import DEBUG_CONFIGS
from terminal_color import Color
from casa.flag_reasons import BAD_ANTENNA_TIME, BAD_BASELINE_TIME
from casa.casa_runner import CasaRunner


class DetailedFlagger:
    def __init__(self, measurement_set):
        self.measurement_set = measurement_set

    def get_bad_antennas(self, source):
        debugger = Debugger(self.measurement_set)
        source_config = ALL_CONFIGS[source]
        scan_ids = self.measurement_set.scan_ids_for(source_config['field'])
        polarizations = GLOBAL_CONFIG['polarizations']
        polarization_and_scan_product = list(itertools.product(polarizations, scan_ids))

        logging.info(Color.HEADER + "Started detailed flagging on all unflagged antennas" + Color.ENDC)
        self._detail_flagging_of_antennas(polarization_and_scan_product, source_config, debugger)

        logging.info(Color.HEADER + "Started detailed flagging on all baselines" + Color.ENDC)
        self._detail_flagging_of_baselines(polarization_and_scan_product, source_config, debugger)

        logging.info(
            "Completed detailed flagging on antennas and baselines, check" + Color.OKBLUE + ' casa_scripts/flags.txt' + Color.ENDC)

    def _detail_flagging_of_antennas(self, polarization_and_scan_product, source_config, debugger):
        bad_antenna_time_present = False
        for polarization, scan_id in polarization_and_scan_product:
            if DEBUG_CONFIGS['manual_flag']: debugger.flag_antennas(polarization, scan_id)
            scan_times = self.measurement_set.timesforscan(scan_id)
            amp_matrix = AmplitudeMatrix(self.measurement_set, polarization, scan_id, source_config['channel'])
            ideal_median = amp_matrix.median()
            ideal_mad = amp_matrix.mad()
            logging.info(
                Color.BACKGROUD_WHITE + "Polarization =" + polarization + " Scan Id=" + str(scan_id) + Color.ENDC)
            logging.debug(
                Color.BACKGROUD_WHITE + "Ideal values = { median:" + str(ideal_median) + ", mad:" + str(
                    ideal_mad) + " }" + Color.ENDC)

            unflagged_antennaids = self.measurement_set.unflagged_antennaids(polarization, scan_id)

            # Sliding Window for Bad Antennas
            for antenna in unflagged_antennaids:
                filtered_matrix = amp_matrix.filter_by_antenna(antenna)
                if filtered_matrix.is_bad(ideal_median, ideal_mad):
                    bad_antenna_time_present = True
                    logging.info(
                        Color.FAIL + 'Antenna ' + str(antenna) + ' is Bad running sliding Window on it' + Color.ENDC)
                    self._flag_bad_time_window(BAD_ANTENNA_TIME, antenna, filtered_matrix.amplitude_data_matrix,
                                               ideal_mad,
                                               ideal_median, scan_times, polarization, scan_id)
        if bad_antenna_time_present:
            logging.info(Color.HEADER + 'Flagging Bad Antenna Time in CASA' + Color.ENDC)
            CasaRunner.flagdata(BAD_ANTENNA_TIME)
        else:
            logging.info(Color.OKGREEN + 'No Bad Antennas were Found' + Color.ENDC)

    def _detail_flagging_of_baselines(self, polarization_and_scan_product, source_config, debugger):
        for polarization, scan_id in polarization_and_scan_product:
            if DEBUG_CONFIGS['manual_flag']: debugger.flag_baselines(polarization, scan_id)
            amp_matrix = AmplitudeMatrix(self.measurement_set, polarization, scan_id, source_config['channel'])
            ideal_median = amp_matrix.median()
            ideal_mad = amp_matrix.mad()
            scan_times = self.measurement_set.timesforscan(scan_id)
            logging.debug(
                Color.BACKGROUD_WHITE + "Polarization =" + polarization + " Scan Id=" + str(scan_id) + Color.ENDC)
            logging.debug(
                Color.BACKGROUD_WHITE + "Ideal values = { median:" + str(ideal_median) + ", mad:" + str(
                    ideal_mad) + " }" + Color.ENDC)

            # Sliding Window for Baselines
            for (baseline, amplitudes) in amp_matrix.amplitude_data_matrix.items():
                self._flag_bad_time_window(BAD_BASELINE_TIME, baseline, {baseline: amplitudes}, ideal_mad, ideal_median,
                                           scan_times, polarization, scan_id)
        logging.info(Color.HEADER + 'Flagging Bad Baselines Time in CASA' + Color.ENDC)
        CasaRunner.flagdata(BAD_BASELINE_TIME)

    def _flag_bad_time_window(self, reason, element_id, data_set, ideal_mad, ideal_median, scan_times, polarization,
                              scan_id):
        sliding_window = Window(data_set)
        while True:
            window_matrix = sliding_window.slide()
            if window_matrix.is_empty() or sliding_window.reached_end_of_collection(): break
            if window_matrix.is_bad(ideal_median, ideal_mad):
                start, end = sliding_window.current_position()
                bad_timerange = scan_times[start], scan_times[end]
                if reason == BAD_ANTENNA_TIME:
                    self.measurement_set.flag_bad_antenna_time(polarization, scan_id, element_id, bad_timerange)
                    logging.debug('Antenna=' + str(element_id) + ' was bad between' + scan_times[
                        start] + '[index=' + str(start) + '] and' + scan_times[end] + '[index=' + str(end) + ']\n')
                else:
                    self.measurement_set.flag_bad_baseline_time(polarization, scan_id, element_id, bad_timerange)
                    logging.debug('Baseline=' + str(element_id) + ' was bad between' + scan_times[
                        start] + '[index=' + str(start) + '] and' + scan_times[end] + '[index=' + str(end) + ']\n')
