# Local Binaries

This directory is for local development tools and binaries that are too large to commit to git.

## act - GitHub Actions Local Runner

To run GitHub Actions workflows locally for testing:

### Installation

**Linux/macOS:**
```bash
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

**Or download from releases:**
https://github.com/nektos/act/releases

After installation, move the `act` binary to this `bin/` directory:
```bash
mv act /path/to/VPNSentinel/bin/
```

### Usage

Run workflows locally:
```bash
./bin/act -l                    # List workflows
./bin/act                       # Run default workflow
./bin/act pull_request          # Run specific event
```

For more information, see: https://github.com/nektos/act
