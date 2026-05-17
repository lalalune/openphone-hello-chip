{
  description = "OpenPhone-AI-SoC hello-chip development shell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-darwin" "aarch64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in {
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = with pkgs; [
            python3
            python3Packages.cocotb
            python3Packages.pytest
            python3Packages.numpy
            verilator
            yosys
            iverilog
            gtkwave
            cmake
            ninja
            qemu
          ];
        };
      });
    };
}
