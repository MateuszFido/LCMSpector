# model.py
import sys, logging
import pandas as pd
import concurrent.futures
from pathlib import Path
from utils.measurements import LCMeasurement, MSMeasurement, Compound

logger = logging.getLogger(__name__)
class Model:
    """
    The Model class handles the loading, processing, and annotation of LC and MS measurement files.

    Attributes
    ----------
    ms_measurements : list
        A list to store MSMeasurement objects.
    lc_measurements : list
        A list to store LCMeasurement objects.
    annotations : list
        A list to store annotations for the measurements.
    lc_results : list
        A list to store results from processing LC files.
    ms_results : list
        A list to store results from processing MS files.

    Methods
    -------
    process_ms_file(ms_file)
        Processes and plots an MS file.
    process_lc_file(lc_file)
        Processes and plots an LC file.
    annotate_ms_file(ms_file)
        Annotates and plots an MS file with compounds.
    preprocess_data(ms_filelist, lc_filelist)
        Preprocesses and annotates LC and MS files concurrently.
    """
    
    __slots__ = ['ms_measurements', 'lc_measurements', 'lc_results', 'ms_results',
    'ion_list', 'compound_cache', 'annotated_ms_measurements', 'annotated_lc_measurements']

    def __init__(self):
        self.ms_measurements = []
        self.lc_measurements = []
        self.lc_results = []
        self.ms_results = []
        self.ion_list = self._initialize_ion_list()
        self.compound_cache = {}
        self.annotated_ms_measurements = {}
        self.annotated_lc_measurements = {}

    def _initialize_ion_list(self):
        return {
            'Adenine':[306.1197,260.0779,476.1776,431.1436,136.0618,134.0472],
            'Adenosine':[438.1620,392.1201,436.1473,268.1041,266.0894],
            'Agmatine':[301.1871,255.1452,471.2450,425.2031,299.1724,129.1145,131.1292],
            'Alanine':[ 260.1129,214.0710,258.0983,90.0550,88.0404],
            'Arginine':[345.1769,299.1350,515.2348,469.1930,343.1623,175.1190,173.1044],
            'Asparagine':[ 303.1187,259.0925,473.1766,427.1348,301.1041,133.0608,131.0462],
            'Aspartic acid':[304.1027,258.0609,302.0881,134.0448,132.0302],
            'Betaine':[118.0863],
            'Cadaverine':[273.1809,227.1391,443.2388,397.1970,271.1663,103.1230,101.1084],
            'Caffeine':[365.1456,195.0877],
            'Choline':[104.1070],
            'Citrulline':[346.1609,300.1191,516.2188,472.1926,344.1463,176.1030,174.0884],
            'Cysteine':[292.0850,246.0431,462.1434,416.1010,290.0703,122.0271,120.0124],
            'DOPA':[368.1340 ,322.0922,366.1194,198.0761,196.0615],
            'Dopamine':[324.1442,278.1023,322.1296,154.0863,152.0717],
            'GABA':[274.1286,228.0867,272.1139,104.0707,102.0560],
            'Glutamic acid':[304.1027,272.0765,302.0881,148.0605,146.0458],
            'Glutamine':[317.1344,271.0925,315.1197,147.0765,145.0618],
            'Glycine':[246.0973,200.0554,244.0826,76.0394,74.0247],
            'Histamine':[282.1449,236.1030,280.1302,112.0870,110.0723],
            'Histidine':[326.1347,280.0928,452.2028,450.1508,324.1201,156.0768,154.0622],
            'Homocitrulline':[360.1766,314.1347,358.1619,190.1187,188.1040],
            'Hypoxanthine':[307.1037,305.0891,137.0458,135.0312],
            'Isoleucine':[302.1599,256.1180,300.1452,132.1020,130.0873],
            'Kynurenine':[379.1500,333.1082,549.2079,503.1661,377.1354,547.1933,209.0921,207.0775],
            'Leucine':[302.1599,258.1336,300.1452,132.1020,130.0873],
            'Lysine':[317.1708,271.1289,487.2287,441.1868,315.1561,485.2140 ,147.1129,145.0982],
            'Methionine':[320.1163,274.0744,318.1016,150.0584,148.0437],
            'NH3':[188.0918,142.0499,358.1497,312.1078,186.0771,18.0339,16.0192],
            'Niacinamide':[293.1132,247.0714,123.0553],
            'Ornithine':[303.1551,257.1132,473.2130,427.1712,301.1405,471.1984,133.0972,131.0826],
            'Orotic acid':[327.0823,497.1402,325.0677,157.0244,155.0098],
            'Phenylalanine':[336.1442,290.1023,334.1296,166.0863,164.0717],
            'Proline':[286.1286,284.1139,116.0707,114.0560],
            'Putrescine':[259.1653,213.1234,429.2232,383.1813,89.1074,87.0927],
            'Riboflavin':[547.2035,545.1889,377.1456,375.1310],
            'SAM':[285.1049,262.0839,370.1338,347.1129,399.1446,398.1372],
            'Serine':[276.1078,230.0660,274.0932,106.0499,104.0353],
            'Serotonin':[347.1602,301.1183,345.1455,177.1023,175.0876],
            'Spermidine':[316.2231,270.1813,486.2810,440.2392,314.2085,146.1652,144.1506],
            'Spermine':[373.2810,327.2391,543.3389,497.2970,371.2663,203.2231,201.2084],
            'TMAO':[230.1387,115.5730,76.0757],
            'Taurine':[296.0799,250.0380,294.0652,126.0220,124.0073],
            'Threonine':[290.1235,244.0816,288.1088,288.1088,118.0509],
            'Tryptamine':[331.1653,285.1234,329.1506,161.1074,159.0927],
            'Tryptophan':[375.1551,329.1132,373.1405,205.0972,203.0826],
            'Tyrosine':[352.1391,306.0973,350.1245,182.0812,180.0666],
            'Uracil':[283.0925,453.1504,113.0346],
            'Urea':[231.0976,401.1555,355.1136,229.0829,61.0397,59.0250],
            'Uridine':[415.1348,414.1274,245.0769,243.0622],
            'Valine':[288.1442,242.1023,287.1369,118.0863,287.1369]}
        
    def process_raw_file(self, file):
        if file.lower().endswith('.mzml'):
            return MSMeasurement(file, 0.0001)
        elif file.lower().endswith('.txt'):
            return LCMeasurement(file)
        else:
            logger.error("Unknown file format.")
            return

    def annotate_ms_file(self, ms_file):
        compound_list = []
        for ion in self.ion_list.keys():
            # Create a unique key for the cache based on the compound name and file
            cache_key = (ion, ms_file.filename)
            if cache_key not in self.compound_cache:
                # Create a new Compound instance and store it in the cache
                compound = Compound(name=ion, file=ms_file.filename, ions=self.ion_list[ion])
                self.compound_cache[cache_key] = compound
            else:
                # Reuse the cached Compound instance
                compound = self.compound_cache[cache_key]
            compound_list.append(compound)
        
        ms_file.annotate(compound_list)
        
        return ms_file
    
    def annotate_lc_file(self, lc_file, annotated_ms_measurements):
        if lc_file.filename not in self.annotated_lc_measurements:
            ms_file_dict = {ms_file.filename: ms_file for ms_file in annotated_ms_measurements}
            corresponding_ms_file = ms_file_dict.get(str(lc_file), None)
            if not corresponding_ms_file:
                logger.error(f"Error processing LC file {lc_file.filename}: No corresponding MS file.")
                return lc_file
            lc_file.annotate(corresponding_ms_file.compounds)
            self.annotated_lc_measurements[lc_file.filename] = lc_file
        else:
            lc_file = self.annotated_lc_measurements[lc_file.filename]
        
        return lc_file

    def _collect_results(self, futures, progress_callback, file_type, offset=0):
        results = []
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            result = None
            try:
                result = future.result()
                results.append(result)
                if progress_callback:
                    progress_callback(int((offset + i + 1) / len(futures) * 100))  # Update progress
            except Exception as e:
                logger.error(f"Error processing {file_type} file {result.filename}: {e}")
        return results

    def process_data(self, ms_filelist, lc_filelist, progress_callback=None):
        total_files = len(ms_filelist) + len(lc_filelist)
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures_ms = {executor.submit(self.process_raw_file, ms_file): ms_file for ms_file in ms_filelist}
            futures_lc = {executor.submit(self.process_raw_file, lc_file): lc_file for lc_file in lc_filelist}

            ms_results = self._collect_results(futures_ms, progress_callback, "MS")
            lc_results = self._collect_results(futures_lc, progress_callback, "LC", len(futures_ms))

        self.ms_results = ms_results
        self.lc_results = lc_results

        return lc_results, ms_results
        

    def annotate_MS(self, progress_callback=None):
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [executor.submit(self.annotate_ms_file, ms_file) for ms_file in self.ms_results]
            annotated_ms_measurements = self._collect_results(futures, progress_callback, "MS")
        self.annotated_ms_measurements = annotated_ms_measurements
        return annotated_ms_measurements


    def annotate_LC(self, progress_callback=None):
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [executor.submit(self.annotate_lc_file, lc_file, self.annotated_ms_measurements) for lc_file in self.lc_results]
            annotated_lc_measurements = self._collect_results(futures, progress_callback, "LC")
        self.annotated_lc_measurements = annotated_lc_measurements
        return annotated_lc_measurements

    def get_plots(self, filename):
        # Find the corresponding MS and LC files
        ms_file = next((ms_file for ms_file in self.annotated_ms_measurements if ms_file.filename == filename), None)
        lc_file = next((lc_file for lc_file in self.annotated_lc_measurements if lc_file.filename == filename), None)
        return lc_file, ms_file


    def save_results(self, lc_file):
        # TODO: Implement
        results = []
        for compound in lc_file.compounds:
            for ion in compound.ions.keys():
                results.append({
                    'File': lc_file.filename,
                    'Ion (m/z)': ion,
                    'Compound': compound.name,
                    'RT (min)': compound.ions[ion]['RT'],
                    'MS Intensity (cps)': compound.ions[ion]['MS Intensity'],
                    'LC Intensity (a.u.)': compound.ions[ion]['LC Intensity']
                })
        df = pd.DataFrame(results)
        df.to_csv('results.csv', index=False)
        
        return
