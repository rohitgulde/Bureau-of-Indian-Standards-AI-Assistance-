import requests
from colorama import Fore, Style, init

init(autoreset=True)

def show_database():
    print(f"\n{Fore.CYAN}==================================================")
    print(f"{Fore.CYAN}       BIS Standards Vector Database (Qdrant)     ")
    print(f"{Fore.CYAN}==================================================\n")

    try:
        status_res = requests.get("http://127.0.0.1:8000/api/ingest/status").json()
        print(f"{Fore.YELLOW}Collection Name : {Style.RESET_ALL}{status_res.get('collection')}")
        print(f"{Fore.YELLOW}Total Documents : {Style.RESET_ALL}{status_res.get('total_vectors')}")
        print(f"{Fore.YELLOW}Vector Dimension: {Style.RESET_ALL}768\n")
        
        print(f"{Fore.CYAN}--- Sample Documents ---\n")
        
        sample_res = requests.get("http://127.0.0.1:8000/api/ingest/sample").json()
        samples = sample_res.get('samples', [])
        
        for i, payload in enumerate(samples):
            print(f"{Fore.GREEN}Document {i+1}")
            print(f"{Fore.MAGENTA}  Standard Code:{Style.RESET_ALL} {payload.get('standard_code', 'N/A')}")
            print(f"{Fore.MAGENTA}  Clause Number:{Style.RESET_ALL} {payload.get('clause_number', 'N/A')}")
            print(f"{Fore.MAGENTA}  Source File  :{Style.RESET_ALL} {payload.get('source_file', 'N/A')}")
            content = payload.get('content_preview', '').replace('\n', ' ').strip()
            print(f"{Fore.MAGENTA}  Text Content :{Style.RESET_ALL} {content}")
            print(f"{Fore.CYAN}  ------------------------------------------------")
            
    except Exception as e:
        print(f"{Fore.RED}Error connecting to backend: {e}")
        print("Make sure Uvicorn is running!")

if __name__ == "__main__":
    show_database()
