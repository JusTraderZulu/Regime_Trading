"""
QuantConnect MCP Client.
Interfaces with QuantConnect cloud via MCP server for automated backtesting.
"""

import base64
import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List

import requests
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class QCBacktestResult(BaseModel):
    """Results from a QuantConnect backtest"""
    
    backtest_id: str
    project_id: str
    status: str
    name: str
    
    # Performance metrics
    sharpe: Optional[float] = None
    cagr: Optional[float] = None
    max_drawdown: Optional[float] = None
    total_return: Optional[float] = None
    win_rate: Optional[float] = None
    
    # Trade statistics
    total_trades: Optional[int] = None
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None
    
    # Metadata
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    completed_at: Optional[datetime] = None
    
    # Raw response
    raw_data: Optional[Dict] = None


class QCMCPClient:
    """
    Client for QuantConnect MCP server.
    Handles backtest submission, monitoring, and result retrieval.
    """
    
    def __init__(
        self,
        api_token: Optional[str] = None,
        user_id: Optional[str] = None,
        mcp_url: str = "http://localhost:8080",
        qc_api_url: str = "https://www.quantconnect.com/api/v2"
    ):
        """
        Initialize QC MCP client.
        
        Args:
            api_token: QuantConnect API token
            user_id: QuantConnect user ID
            mcp_url: MCP server URL (if running locally)
            qc_api_url: QuantConnect API base URL
        """
        self.api_token = api_token
        self.user_id = user_id
        self.mcp_url = mcp_url
        self.qc_api_url = qc_api_url
        
        # Load credentials if not provided
        if not self.api_token or not self.user_id:
            self._load_credentials()
    
    def _get_auth_headers(self) -> Dict:
        """
        Get authentication headers for QC API.
        Uses the official QC authentication scheme:
        1. Hash = SHA256(api_token:timestamp)
        2. Auth = Base64(user_id:hash)
        
        Reference: https://www.quantconnect.com/docs/v2/cloud-platform/api-reference/authentication
        """
        timestamp = str(int(time.time()))
        
        # Step 1: Create hashed token
        time_stamped_token = f'{self.api_token}:{timestamp}'.encode('utf-8')
        hashed_token = hashlib.sha256(time_stamped_token).hexdigest()
        
        # Step 2: Create authentication string
        authentication = f'{self.user_id}:{hashed_token}'.encode('utf-8')
        authentication_encoded = base64.b64encode(authentication).decode('ascii')
        
        return {
            'Authorization': f'Basic {authentication_encoded}',
            'Timestamp': timestamp
        }
    
    def _load_credentials(self):
        """Load QC credentials from .env file or fallback to .txt files"""
        try:
            # Priority 1: Try .env file
            env_path = Path(".env")
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("QC_API_TOKEN="):
                            self.api_token = line.split("=", 1)[1].strip()
                        elif line.startswith("QC_USER_ID="):
                            self.user_id = line.split("=", 1)[1].strip()
            
            # Priority 2: Fallback to separate .txt files (backward compatibility)
            if not self.api_token:
                qc_token_path = Path("qc_token.txt")
                if qc_token_path.exists():
                    self.api_token = qc_token_path.read_text().strip()
            
            if not self.user_id:
                qc_user_path = Path("qc_user.txt")
                if qc_user_path.exists():
                    self.user_id = qc_user_path.read_text().strip()
            
            # Log what was loaded
            if self.api_token and self.user_id:
                logger.debug(f"QC credentials loaded (User: {self.user_id})")
            else:
                logger.warning("QC credentials not found in .env or .txt files")
                
        except Exception as e:
            logger.warning(f"Could not load QC credentials: {e}")
    
    def upload_algorithm(
        self,
        algorithm_path: Path,
        project_id: str,
        file_name: str = "main.py"
    ) -> bool:
        """
        Upload or update algorithm Python file to a QC project.
        
        Args:
            algorithm_path: Path to Python algorithm file
            project_id: QC project ID
            file_name: Name for the file in QC (default: main.py)
        
        Returns:
            True if successful
        """
        if not self.api_token or not self.user_id:
            logger.error("QC credentials not configured")
            return False
        
        # Read file content
        with open(algorithm_path, 'r') as f:
            content = f.read()
        
        # Try update first (file might exist)
        url_update = f"{self.qc_api_url}/files/update"
        headers = self._get_auth_headers()
        
        data = {
            'projectId': project_id,
            'name': file_name,
            'content': content
        }
        
        try:
            response = requests.post(url_update, json=data, headers=headers)
            result = response.json()
            
            if result.get('success'):
                logger.info(f"✓ Updated {file_name} in project {project_id}")
                return True
            elif 'not found' in str(result.get('errors', '')).lower():
                # File doesn't exist, try create instead
                url_create = f"{self.qc_api_url}/files/create"
                
                with open(algorithm_path, 'rb') as f:
                    files = {'file': (file_name, f, 'text/x-python')}
                    form_data = {
                        'projectId': project_id,
                        'name': file_name
                    }
                    
                    response = requests.post(url_create, files=files, data=form_data, headers=headers)
                    result = response.json()
                    
                    if result.get('success'):
                        logger.info(f"✓ Created {file_name} in project {project_id}")
                        return True
            
            logger.error(f"Upload failed: {result.get('errors')}")
            return False
                    
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return False
    
    def compile_project(
        self,
        project_id: str
    ) -> Optional[str]:
        """
        Compile a QC project.
        
        Args:
            project_id: QC project ID
        
        Returns:
            Compile ID if successful
        """
        if not self.api_token or not self.user_id:
            logger.error("QC credentials not configured")
            return None
        
        url = f"{self.qc_api_url}/compile/create"
        
        headers = self._get_auth_headers()
        
        data = {
            'projectId': project_id
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            result = response.json()
            
            if result.get('success'):
                compile_id = result.get('compileId')
                state = result.get('state', 'Unknown')
                logger.info(f"✓ Compilation started: {compile_id} (state={state})")
                
                # If already successful, return immediately
                if state == 'BuildSuccess':
                    logger.info(f"✓ Compilation successful")
                    return compile_id
                
                # Wait for compilation to complete
                logger.info("Waiting for compilation to complete...")
                max_wait = 30  # 30 seconds
                for i in range(max_wait):
                    time.sleep(2)
                    
                    # Check compile status
                    compile_check_url = f"{self.qc_api_url}/compile/read"
                    compile_params = {'projectId': project_id, 'compileId': compile_id}
                    compile_check = requests.get(compile_check_url, params=compile_params, headers=headers)
                    compile_result = compile_check.json()
                    
                    if compile_result.get('success'):
                        state = compile_result.get('state', 'Unknown')
                        logger.info(f"  Compile status: {state}")
                        
                        if state == 'BuildSuccess':
                            logger.info(f"✓ Compilation successful")
                            return compile_id
                        elif 'error' in state.lower():
                            logger.error(f"Compilation failed: {state}")
                            return None
                
                logger.warning(f"Compilation timeout, but using compile ID")
                return compile_id
            else:
                logger.error(f"Compilation failed: {result.get('errors')}")
                return None
                
        except Exception as e:
            logger.error(f"Compilation error: {e}")
            return None
    
    def create_backtest(
        self,
        project_id: str,
        compile_id: str,
        backtest_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Create and run a backtest.
        
        Args:
            project_id: QC project ID
            compile_id: Compile ID from compile_project()
            backtest_name: Optional name for the backtest
        
        Returns:
            Backtest ID if successful
        """
        if not self.api_token or not self.user_id:
            logger.error("QC credentials not configured")
            return None
        
        if not backtest_name:
            backtest_name = f"Regime_Backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        url = f"{self.qc_api_url}/backtests/create"
        
        headers = self._get_auth_headers()
        
        data = {
            'projectId': project_id,
            'compileId': compile_id,
            'backtestName': backtest_name
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            result = response.json()
            
            logger.debug(f"Backtest creation response: {result}")
            
            if result.get('success'):
                # QC might return different field names
                backtest_id = result.get('backtestId') or result.get('backtest_id') or result.get('backtest', {}).get('backtestId')
                
                if backtest_id:
                    logger.info(f"✓ Created backtest: {backtest_id}")
                    return backtest_id
                else:
                    logger.error(f"Backtest created but no ID returned: {result}")
                    return None
            else:
                logger.error(f"Backtest creation failed: {result.get('errors')}")
                return None
                
        except Exception as e:
            logger.error(f"Backtest creation error: {e}")
            return None
    
    def get_backtest_status(
        self,
        project_id: str,
        backtest_id: str
    ) -> Optional[Dict]:
        """
        Get backtest status and results.
        
        Args:
            project_id: QC project ID
            backtest_id: Backtest ID
        
        Returns:
            Backtest data dict
        """
        if not self.api_token:
            logger.error("QC credentials not configured")
            return None
        
        url = f"{self.qc_api_url}/backtests/read"
        
        headers = self._get_auth_headers()
        
        params = {
            'projectId': project_id,
            'backtestId': backtest_id
        }
        
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                return result.get('backtest', {})
            else:
                logger.error(f"Status check failed: {result.get('errors')}")
                return None
                
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return None
    
    def wait_for_backtest(
        self,
        project_id: str,
        backtest_id: str,
        timeout: int = 600,
        poll_interval: int = 10
    ) -> Optional[QCBacktestResult]:
        """
        Wait for backtest to complete and return results.
        
        Args:
            project_id: QC project ID
            backtest_id: Backtest ID
            timeout: Max seconds to wait
            poll_interval: Seconds between status checks
        
        Returns:
            QCBacktestResult if successful
        """
        logger.info(f"Waiting for backtest {backtest_id} (timeout={timeout}s)...")
        
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            status_data = self.get_backtest_status(project_id, backtest_id)
            
            if not status_data:
                logger.warning("Could not fetch backtest status")
                time.sleep(poll_interval)
                continue
            
            status = status_data.get('status', 'Unknown')
            progress = status_data.get('progress', 0)
            
            logger.info(f"  Status: {status} | Progress: {progress}%")
            
            if status == 'Completed':
                # Extract results
                return self._parse_backtest_results(
                    project_id=project_id,
                    backtest_id=backtest_id,
                    data=status_data
                )
            elif status in ['Error', 'Cancelled']:
                logger.error(f"Backtest {status.lower()}: {status_data.get('error')}")
                return None
            
            time.sleep(poll_interval)
        
        logger.error(f"Backtest timed out after {timeout}s")
        return None
    
    def _parse_backtest_results(
        self,
        project_id: str,
        backtest_id: str,
        data: Dict
    ) -> QCBacktestResult:
        """Parse QC backtest results into our model"""
        
        # Extract statistics
        statistics = data.get('statistics', {})
        
        result = QCBacktestResult(
            backtest_id=backtest_id,
            project_id=project_id,
            status=data.get('status', 'Unknown'),
            name=data.get('name', ''),
            sharpe=self._safe_float(statistics.get('Sharpe Ratio')),
            cagr=self._safe_float(statistics.get('Compounding Annual Return')),
            max_drawdown=self._safe_float(statistics.get('Drawdown')),
            total_return=self._safe_float(statistics.get('Total Net Profit')),
            win_rate=self._safe_float(statistics.get('Win Rate')),
            total_trades=self._safe_int(statistics.get('Total Orders')),
            start_date=data.get('startDate'),
            end_date=data.get('endDate'),
            completed_at=datetime.now(),
            raw_data=data
        )
        
        logger.info(f"✓ Backtest complete: Sharpe={result.sharpe:.2f}, CAGR={result.cagr:.2%}")
        
        return result
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert to float"""
        try:
            if value is None or value == '':
                return None
            # Remove % and convert
            if isinstance(value, str):
                value = value.replace('%', '').strip()
            return float(value)
        except:
            return None
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert to int"""
        try:
            if value is None or value == '':
                return None
            return int(float(value))
        except:
            return None
    
    def run_full_backtest(
        self,
        algorithm_path: Path,
        project_id: str,
        backtest_name: Optional[str] = None,
        wait: bool = True
    ) -> Optional[QCBacktestResult]:
        """
        Complete workflow: upload algorithm, create backtest, wait for results.
        
        Args:
            algorithm_path: Path to Python algorithm file (with embedded signals)
            project_id: QC project ID
            backtest_name: Optional name for backtest
            wait: If True, wait for completion
        
        Returns:
            QCBacktestResult if successful and wait=True
        """
        logger.info("🚀 Starting QC backtest workflow...")
        
        # Step 1: Upload algorithm (always upload as main.py to replace)
        if not self.upload_algorithm(algorithm_path, project_id, file_name="main.py"):
            logger.error("Failed to upload algorithm")
            return None
        
        # Step 2: Compile project
        logger.info("Compiling project...")
        compile_id = self.compile_project(project_id)
        if not compile_id:
            logger.error("Failed to compile project")
            return None
        
        # Step 3: Create backtest
        backtest_id = self.create_backtest(project_id, compile_id, backtest_name)
        if not backtest_id:
            logger.error("Failed to create backtest")
            return None
        
        # Step 4: Wait for results
        if wait:
            return self.wait_for_backtest(project_id, backtest_id)
        else:
            logger.info(f"Backtest {backtest_id} started (not waiting)")
            return None

