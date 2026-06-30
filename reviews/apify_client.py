from apify_client import ApifyClient

# This is now a thin wrapper around the real client for consistency,
# though it could be used directly.
class ApifyClientWrapper:
    def __init__(self, api_token: str):
        if not api_token:
            raise ValueError("Apify API token is required.")
        self.client = ApifyClient(api_token)

    def start_scraper(self, scraper_identifier: str, input_data: dict) -> dict:
        """
        Starts an actor on Apify and returns the run object.
        """
        print(f"Starting scraper '{scraper_identifier}' on Apify...")
        run = self.client.actor(scraper_identifier).call(run_input=input_data)
        return run

    def get_run_results(self, run_info: dict) -> list:
        """
        Fetches all items from a run's default dataset.
        """
        dataset_id = run_info.get("defaultDatasetId")
        if not dataset_id:
            return []

        print(f"Fetching results from dataset '{dataset_id}'...")
        items = list(self.client.dataset(dataset_id).iterate_items())
        print(f"Fetched {len(items)} items.")
        return items
