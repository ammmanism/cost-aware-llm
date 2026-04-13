import heapq
from typing import List, Tuple

class PriorityQueueBalancer:
    def __init__(self, endpoints_with_priority: List[Tuple[int, str]]):
        self.pq = endpoints_with_priority
        heapq.heapify(self.pq)

    def get_endpoint(self) -> str:
        priority, endpoint = heapq.heappop(self.pq)
        # Re-insert with same priority for demo, in reality priority might change
        heapq.heappush(self.pq, (priority, endpoint))
        return endpoint
