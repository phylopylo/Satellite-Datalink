{
	description = "Satellite Datalink Environment";
	
	inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

	outputs = { self, nixpkgs }:

	let
		systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
		description = "Satellite Datalink Environment";
		forAllSystems = f: nixpkgs.lib.genAttrs systems
			(system: f nixpkgs.legacyPackages.${system});
	in {
		devShells = forAllSystems (pkgs: {
			default = pkgs.mkShell {
				packages = with pkgs; [

					gcc
					cmake
					gnumake
				];

				shellHook = ''
				  PS1="\n\[\033[1;32m\][\u@\h\[\033[1;34m\]\[\033[1;32m\]:\w]\$\[\033[0m\] "
				'';
			};
		});
	};
}
