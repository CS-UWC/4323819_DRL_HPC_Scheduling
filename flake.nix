{
  description = "Python RL scheduling environment (GPU container, CPU/AMD host shell)";

  nixConfig = {
    extra-substituters = [ "https://cache.nixos-cuda.org" ];
    extra-trusted-public-keys = [ "cache.nixos-cuda.org:74DUi4Ye579gUqzH4ziL9IyiJBlDpMRn9MBN8oNan9M=" ];
  };

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    nixpkgs-stable.url = "github:NixOS/nixpkgs/nixos-25.05";
    utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, nixpkgs-stable, utils }:
    let
      system = "x86_64-linux";

      # Single overlay: replaces source PyTorch with binary wheels.
      # The binary wheels ignore config.cudaSupport and ship their own CUDA runtime.
      torchBinOverlay = final: prev: {
        python312 = prev.python312.override {
          packageOverrides = pyFinal: pyPrev: {
            torch = pyPrev.torch-bin;
            torchvision = pyPrev.torchvision-bin;
            stable-baselines3 = pyPrev.stable-baselines3.overridePythonAttrs (old: { doCheck = false; });
            gymnasium = pyPrev.gymnasium.overridePythonAttrs (old: { doCheck = false; });
          };
        };
      };

      # Single package set without global cudaSupport; torch-bin supplies CUDA user space.
      pkgs = import nixpkgs-stable {
        inherit system;
        config = { allowUnfree = true; };
        overlays = [ torchBinOverlay ];
      };

      # Lightweight contract-test environment; deliberately excludes PyTorch/CUDA.
      testPythonEnv = pkgs.python312.withPackages (ps: with ps; [
        numpy pandas scipy networkx gymnasium python-dateutil
        (ps.callPackage ./nix/paretoset.nix {})
      ]);

      testRunner = pkgs.writeShellApplication {
        name = "drl-scheduler-tests";
        runtimeInputs = [ testPythonEnv pkgs.bash pkgs.rsync ];
        text = ''
          python -W error::ResourceWarning -m unittest discover -s tests -v
        '';
      };

      # Full training and workflow environment.
      myPythonEnv = pkgs.python312.withPackages (ps: with ps; [
        numpy pandas matplotlib pillow sympy networkx
        gymnasium torch torchvision stable-baselines3
        tensorboard tensorboard-data-server protobuf grpcio markdown
        cloudpickle filelock fsspec packaging six typing-extensions
        tzdata pytz scikit-posthocs scipy python-dateutil

        # Custom derivations
        (ps.callPackage ./nix/sb3-contrib.nix {})
        (ps.callPackage ./nix/paretoset.nix {})
        (ps.callPackage ./nix/snakemake_slurm.nix {})
        (ps.callPackage ./nix/snakemake_slurm_jobstep.nix {})
      ]);
    in {
      apps.${system}.test = {
        type = "app";
        program = "${testRunner}/bin/drl-scheduler-tests";
        meta.description = "Run contract tests without PyTorch or CUDA";
      };

      devShells.${system} = {
        test = pkgs.mkShell {
          packages = [ testPythonEnv pkgs.rsync ];
        };

        default = pkgs.mkShell {
          # Optional: expose GPU on nvidia hosts via host driver
          LD_LIBRARY_PATH = "/run/opengl-driver/lib";
          packages = [ myPythonEnv pkgs.snakemake pkgs.graphviz pkgs.just pkgs.skopeo pkgs.apptainer pkgs.rsync pkgs.tmux ];
        };
      };

      # GPU-enabled PyTorch without pulling cudaSupport into every other package.
      # torch-bin bundles its own CUDA runtime; works inside the container
      # if the host driver is mounted (e.g. apptainer --nv).
      packages.${system}.container = pkgs.dockerTools.streamLayeredImage {
        name = "DRL_env";
        tag = "latest";
        contents = pkgs.buildEnv {
          name = "image-root";
          paths = [ myPythonEnv pkgs.snakemake pkgs.coreutils pkgs.bashInteractive ];
          pathsToLink = [ "/" ];
        };
        config = { Env = [ "PATH=${myPythonEnv}/bin:${pkgs.snakemake}/bin" ]; };
      };
    };
}
