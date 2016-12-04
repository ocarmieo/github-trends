from itertools import combinations
from mrjob.job import MRJob
import json
import logging


class MRNodeCount(MRJob):

    def mapper(self, _, line):
        try:
            json_data = json.loads(line)
        except ValueError as e:
            logging.error(e)
            return
            
        package_list = json_data['packages']
        for package in package_list:
            yield package, 1

    def reducer(self, package, counts):
        yield package, sum(counts)


if __name__ == '__main__':
    MRNodeCount.run()
    # python mrjobcode.py directory_of_files > redirect
    # python mr_nodes.py -r emr -c ~/.mrjob.conf s3://github-trends/edges/* > node_counts