from itertools import combinations
from mrjob.job import MRJob
import json
import logging


class MREgdeCount(MRJob):

    def mapper(self, _, line):
        try:
            json_data = json.loads(line)
        except ValueError as e:
            logging.error(e)
            return
            
        id = json_data['file_id']
        package_list = sorted(json_data['packages'])
        for pair in combinations(package_list, 2):
            yield pair, 1

    def reducer(self, pair, counts):
        yield pair, sum(counts)


if __name__ == '__main__':
    MREgdeCount.run()
    # python mrjobcode.py directory_of_files > redirect
    # python mr_edges.py -r emr -c ~/.mrjob.conf s3://github-trends/edges/* > edge_counts