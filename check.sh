#flake8 nyan/ --count --ignore=C901,E741,W503,PIE786,E203 --show-source --statistics
#flake8 nyan/ --count --exit-zero --max-complexity=10 --statistics
#mypy --strict nyan/

flake8 nyan/ --count --ignore=C901,E741,W503,PIE786,E203 --show-source --statistics
flake8 nyan/ --count --exit-zero --show-source --statistics
mypy --strict nyan/
