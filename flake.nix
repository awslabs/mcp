{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixpkgs-unstable";
  };
  outputs = { self, nixpkgs, ... }:
  let
    forAllSystems = f: nixpkgs.lib.genAttrs [ "x86_64-linux" "aarch64-linux" ] ( system:
      f (import nixpkgs { inherit system; })
    );
    mkLibraryPath = pkgs: with pkgs; lib.makeLibraryPath [
     stdenv.cc.cc  # numpy (on which scenedetect depends) needs C libraries
    ];
    pythonForPkgs = pkgs: pkgs.python313;
  in
  {
    devShells = forAllSystems (pkgs:
      let
        python = pythonForPkgs pkgs;
        pythonPackages = python.pkgs;
      in
      {
        default = with pkgs; with pythonPackages;
      pkgs.mkShell {
        packages = [
          python
          uv
          ruff
        ];

          # export "LD_LIBRARY_PATH=$LD_LIBRARY_PATH:${mkLibraryPath pkgs}"
        shellHook = ''
          export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${mkLibraryPath pkgs}"
          export UV_PYTHON_DOWNLOADS=never
          
          exec -l zsh
        '';
      };
    });
  };
}




