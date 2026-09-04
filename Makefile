.PHONY: test install

test:
	cd backend && python -m pytest -q

install:
	sudo ./install.sh
