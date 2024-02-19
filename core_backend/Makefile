#!make

.PHONY : tests

PROJECT_NAME = aaq-core
CONDA_ACTIVATE=source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate ; conda activate
ENDPOINT_URL = localhost:8000

clean:
	find .. -type f -name "*.py[co]" -delete
	find .. -type d -name "__pycache__" -delete
	find .. -type d -name ".pytest_cache" -delete

# Note: Run `make fresh-env psycopg2-binary=true` to manually replace psycopg with psycopg2-binary
fresh-env :
	conda remove --name $(PROJECT_NAME) --all -y
	conda create --name $(PROJECT_NAME) python==3.11 -y

	$(CONDA_ACTIVATE) $(PROJECT_NAME); \
	pip install -r requirements.txt --ignore-installed; \
	pip install -r ../requirements-dev.txt --ignore-installed; \
	pre-commit install

	if [ "$(psycopg2-binary)" = "true" ]; then \
		$(CONDA_ACTIVATE) $(PROJECT_NAME); \
		pip uninstall -y psycopg2==2.9.9; \
		pip install psycopg2-binary==2.9.9; \
	fi

# Running Tests
tests: setup-test-containers run-tests teardown-test-containers
run-tests:
	@set -a && source ./tests/api/test.env && set +a && \
	python -m alembic upgrade head && \
	python -m pytest -rPQ -m "not rails"

# Test DBs
setup-test-containers: setup-test-relational-db  setup-alignscore-container

teardown-test-containers: stop-test-relational-db  stop-alignscore-container

setup-test-relational-db:
	-@docker stop testdb
	-@docker rm testdb
	@docker system prune -f
	@sleep 2
	@set -a && source ./tests/api/test.env && set +a && \
	docker run --name testdb \
		-p 5433:5432 \
		-e POSTGRES_PASSWORD \
		-e POSTGRES_USER \
		-e POSTGRES_DB \
		-d pgvector/pgvector:pg16
	@set -a && source ./tests/api/test.env && set +a && \
	python -m alembic upgrade head

setup-alignscore-container:
	-@docker stop testalignscore
	-@docker rm testalignscore
	docker run --name testalignscore \
		-p 5002:5001 \
		-d alignscore-base:latest
	@sleep 10

stop-alignscore-container:
	@docker stop testalignscore
	@docker rm testalignscore

stop-test-relational-db:
	@docker stop testdb
	@docker rm testdb

# Development DB

setup-dbs: setup-relational-db

teardown-dbs: stop-relational-db

# load some dummy FAQs into the content table
add-dummy-faqs:
	curl -X POST -d '{"content_title": "Come camping", "content_text":"Embrace the call of the wild with camping, an age-old tradition that reconnects us with nature. Whether youre pitching a tent under a canopy of stars or sharing stories around a crackling campfire, camping offers a unique escape from the hustle and bustle of daily life. Experience the tranquility of the great outdoors and create lasting memories with loved ones."}' -H 'Content-Type: application/json' $(ENDPOINT_URL)/content/create
	curl -X POST -d '{"content_title": "On Music", "content_text":"Music is the universal language of the soul, transcending borders and resonating with hearts across the globe. From the rhythmic beats of a drum to the melodic strains of a violin, music has the power to evoke emotions, memories, and even change moods. Whether youre a creator or a listener, music is a journey of self-expression and discovery."}' -H 'Content-Type: application/json' $(ENDPOINT_URL)
	curl -X POST -d '{"content_title": "Go Squash", "content_text":"Dive into the fast-paced world of squash, a racquet sport that demands agility, strategy, and stamina. Played within four walls, players take turns hitting a small rubber ball, aiming to outmaneuver their opponent. With its roots dating back centuries, squash is not just a test of physical prowess but also a mental challenge, making every match an exhilarating experience."}' -H 'Content-Type: application/json' $(ENDPOINT_URL)/content/create
	curl -X POST -d '{"content_title": "Eat Squash", "content_text":"Squash, a versatile and nutritious vegetable, graces tables in various forms, from zesty summer varieties to hearty winter ones. Whether roasted, pureed, or stir-fried, squash offers a delightful mix of flavors and textures. Rich in vitamins and fiber, this humble vegetable is a staple in many cuisines, celebrating the bounty of the harvest season."}' -H 'Content-Type: application/json' $(ENDPOINT_URL)/content/create
	curl -X POST -d '{"content_title": "The racquet", "content_text":"The tennis racquet, an extension of a players arm, is a marvel of engineering and design. From its early wooden iterations to todays advanced composite materials, the racquet has evolved to enhance performance on the court. With the right balance, weight, and string tension, a tennis racquet can make all the difference in those match-winning shots."}' -H 'Content-Type: application/json' $(ENDPOINT_URL)/content/create
	curl -X POST -d '{"content_title": "Try Coffee", "content_text":"From the aromatic scent of freshly ground beans to the invigorating first sip in the morning, coffee is more than just a beverage—its an experience. Originating from ancient Ethiopian plateaus, coffee has traveled the world, with each region offering its unique blend and roast. Whether youre a latte lover or an espresso enthusiast, coffee promises a rich journey with every cup."}' -H 'Content-Type: application/json' $(ENDPOINT_URL)/content/create
	curl -X POST -d '{"content_title": "Astronomy", "content_text":"Venture beyond our blue planet and into the vast expanse of the universe with astronomy. This ancient science invites us to ponder the mysteries of stars, galaxies, and black holes. With telescopes as our windows, we can explore cosmic wonders, witness celestial events, and even trace our own place within this grand cosmic tapestry."}' -H 'Content-Type: application/json' $(ENDPOINT_URL)/content/create
	curl -X POST -d '{"content_title": "Yoga", "content_text":"Yoga, an ancient practice rooted in Indian philosophy, harmonizes the body, mind, and spirit. Through a combination of postures, breathing exercises, and meditation, yoga offers a holistic approach to wellness. Whether youre seeking physical flexibility, mental clarity, or spiritual growth, yoga provides a path to self-discovery and inner peace."}' -H 'Content-Type: application/json' $(ENDPOINT_URL)/content/create
	curl -X POST -d '{"content_title": "Digital art", "content_text":"In the intersection of technology and creativity lies digital art, a modern medium that pushes the boundaries of traditional artistry. With tools like graphic tablets and software, artists can create mesmerizing visuals, intricate designs, and immersive animations. Digital art not only showcases the evolution of art but also the limitless potential of human imagination when paired with technology."}' -H 'Content-Type: application/json' $(ENDPOINT_URL)/content/create

setup-relational-db:
	-@docker stop postgres-local
	-@docker rm postgres-local
	@docker system prune -f
	@sleep 2
	@docker run --name postgres-local \
     -e POSTGRES_PASSWORD=postgres \
     -p 5432:5432 \
     -d pgvector/pgvector:pg16
	python -m alembic upgrade head

stop-relational-db:
	@docker stop postgres-local
	@docker rm postgres-local
