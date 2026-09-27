
cmake:
	cmake -S . -B build
.PHONY: cmake

build:
	cmake --build build
.PHONY: build

satellite: build
	./build/satellite
.PHONY: satellite

ground: build
	./build/ground
.PHONY: ground
