# Db_tester

Database performance testing utility


## Installation

Clone the project

```bash
  git clone https://github.com/yudakov1814/db_tester
```

Go to the project directory

```bash
  cd db_tester
```

Create virtual env

```bash
  python3 -m venv venv
```

Activate created venv

```bash
  source venv/bin/activate
```

Upgrade pip

```bash
  pip install --upgrade pip
```

Install dependencies

```bash
  pip install -r requirements.txt
```


## Run

For detailed information, use help

```bash
  python3 main.py --help
```

Generate 5 records and put them in dataset.json

```bash
  python3 main.py generate -s 5 --scheme schemes.json -o dataset.json
```

Run tests on PostgreSQL and MySQL

```bash
  python3 main.py run -s 100 -db PostgreSQL -db MySQL --conn conn.json --scheme schemes.json -t test_cases.json
```
