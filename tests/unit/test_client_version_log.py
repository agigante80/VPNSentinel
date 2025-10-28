import os
import subprocess
import unittest


class TestClientVersionLog(unittest.TestCase):
    def test_version_line_in_startup(self):
        """Run the client script with VERSION and COMMIT_HASH set and check stdout for the version line"""
        script_path = os.path.join(os.path.dirname(__file__), '..', '..', 'vpn-sentinel-client', 'vpn-sentinel-client.sh')
        script_path = os.path.normpath(script_path)

        # Use a short run of the script: run it but immediately exit after printing startup logs
        # We achieve this by invoking bash -c to source the script and then exit; the script itself loops,
        # so instead run the script but with INTERVAL=0 and trap to exit after startup logs are printed.
        env = os.environ.copy()
        env['VERSION'] = '1.2.3-test'
        env['COMMIT_HASH'] = 'deadbeef'
        env['INTERVAL'] = '0'

        # Run the script and capture stdout/stderr; ensure it exits quickly
        try:
            # Run the script and allow it to run briefly; capture stdout even if it times out
            result = subprocess.run(['bash', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True, timeout=5)
            output = result.stdout
        except subprocess.TimeoutExpired as e:
            # The script is expected to run indefinitely; a timeout is fine — capture partial output
            output = e.stdout or b''

        # Ensure we have a str to search (TimeoutExpired may return bytes)
        if isinstance(output, bytes):
            output = output.decode('utf-8', errors='ignore')

        # Assert that the version line appears in the captured output
        self.assertTrue(('📦 Version:' in output) or ('Version:' in output), f"Version line not found in output:\n{output}")


if __name__ == '__main__':
    unittest.main()
