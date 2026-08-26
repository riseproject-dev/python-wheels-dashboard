import datetime as dt
import json
import re
import requests_cache


BASE_URL = "https://pypi.org/pypi"
RISE_REGISTRY_URL = "https://pypi.riseproject.dev/simple"

DEPRECATED_PACKAGES = {
    "BeautifulSoup",
    "bs4",
    "distribute",
    "django-social-auth",
    "nose",
    "pep8",
    "pycrypto",
    "pypular",
    "sklearn",
    "y-py",
}

# Packages we deliberately do not port to riscv64, and why.
IGNORED_PACKAGES = {
    # Proprietary GPU/vendor blobs, x86_64 and aarch64 only
    "cuda-bindings",
    "cuda-core",
    "nvidia-cublas",
    "nvidia-cublas-cu12",
    "nvidia-cuda-cupti",
    "nvidia-cuda-cupti-cu12",
    "nvidia-cuda-nvrtc",
    "nvidia-cuda-nvrtc-cu12",
    "nvidia-cuda-runtime",
    "nvidia-cuda-runtime-cu12",
    "nvidia-cudnn-cu12",
    "nvidia-cudnn-cu13",
    "nvidia-cufft",
    "nvidia-cufft-cu12",
    "nvidia-cufile",
    "nvidia-cufile-cu12",
    "nvidia-curand",
    "nvidia-curand-cu12",
    "nvidia-cusolver",
    "nvidia-cusolver-cu12",
    "nvidia-cusparse",
    "nvidia-cusparse-cu12",
    "nvidia-cusparselt-cu13",
    "nvidia-cutlass-dsl-libs-base",
    "nvidia-nccl-cu12",
    "nvidia-nccl-cu13",
    "nvidia-nvjitlink",
    "nvidia-nvjitlink-cu12",
    "nvidia-nvshmem-cu12",
    "nvidia-nvshmem-cu13",
    "nvidia-nvtx",
    "triton",
    # Windows only
    "pywin32",
    "pywinpty",
    "triton-windows",
    "winkerberos",
    # macOS only
    "pyobjc-core",
    "pyobjc-framework-cocoa",
    "pyobjc-framework-quartz",
    "pyobjc-framework-applicationservices",
    "pyobjc-framework-coretext",
    "pyobjc-framework-security",
    "pyobjc-framework-webkit",
    "pyobjc-framework-corebluetooth",
    "pyobjc-framework-coreml",
    "pyobjc-framework-vision",
    "pyobjc-framework-libdispatch",
    "pyobjc-framework-coremedia",
    "pyobjc-framework-coreaudio",
    "pyobjc-framework-fsevents",
    "pyobjc-framework-avfoundation",
    "pyobjc-framework-corelocation",
    "pyobjc-framework-metal",
    "pyobjc-framework-systemconfiguration",
    "pyobjc-framework-contacts",
    "pyobjc-framework-coreservices",
    "pyobjc-framework-photos",
    "pyobjc-framework-spritekit",
    "pyobjc-framework-cfnetwork",
    "pyobjc-framework-addressbook",
    "pyobjc-framework-localauthentication",
    "pyobjc-framework-coredata",
    "pyobjc-framework-automator",
    "pyobjc-framework-discrecording",
    "pyobjc-framework-screensaver",
    "pyobjc-framework-syncservices",
    "pyobjc-framework-coreaudiokit",
    "pyobjc-framework-corewlan",
    "pyobjc-framework-securityinterface",
    "pyobjc-framework-speech",
    "pyobjc-framework-coremidi",
    "pyobjc-framework-screencapturekit",
    "pyobjc-framework-avkit",
    "pyobjc-framework-usernotifications",
    "pyobjc-framework-corespotlight",
    "pyobjc-framework-imagecapturecore",
    "pyobjc-framework-cryptotokenkit",
    "pyobjc-framework-scriptingbridge",
    "pyobjc-framework-gamecenter",
    "pyobjc-framework-contactsui",
    "pyobjc-framework-metalperformanceshaders",
    "pyobjc-framework-gamecontroller",
    "pyobjc-framework-coremediaio",
    "pyobjc-framework-intents",
    "pyobjc-framework-storekit",
    "pyobjc-framework-mapkit",
    "pyobjc-framework-accessibility",
    "pyobjc-framework-photosui",
    "pyobjc-framework-multipeerconnectivity",
    "pyobjc-framework-authenticationservices",
    "pyobjc-framework-externalaccessory",
    "pyobjc-framework-modelio",
    "pyobjc-framework-fileprovider",
    "pyobjc-framework-networkextension",
    "pyobjc-framework-scenekit",
    "pyobjc-framework-mediatoolbox",
    "pyobjc-framework-audiovideobridging",
    "pyobjc-framework-videotoolbox",
    "pyobjc-framework-coremotion",
    "pyobjc-framework-notificationcenter",
    "pyobjc-framework-gamekit",
    "pyobjc-framework-network",
    "pyobjc-framework-gameplaykit",
    "pyobjc-framework-automaticassessmentconfiguration",
    "pyobjc-framework-safariservices",
    "pyobjc-framework-metalkit",
    "pyobjc-framework-callkit",
    "pyobjc-framework-pushkit",
    "pyobjc-framework-classkit",
    "pyobjc-framework-oslog",
    "pyobjc-framework-systemextensions",
    "pyobjc-framework-passkit",
    "pyobjc-framework-replaykit",
    "pyobjc-framework-virtualization",
    "pyobjc-framework-intentsui",
    "pyobjc-framework-metrickit",
    "pyobjc-framework-shazamkit",
    "pyobjc-framework-sharedwithyoucore",
    "pyobjc-framework-iobluetooth",
    "pyobjc-framework-libxpc",
    "pyobjc-framework-backgroundassets",
    "pyobjc-framework-avrouting",
    "pyobjc-framework-healthkit",
    "pyobjc-framework-metalfx",
    "pyobjc-framework-extensionkit",
    "pyobjc-framework-safetykit",
    "pyobjc-framework-sharedwithyou",
    "pyobjc-framework-browserenginekit",
    "pyobjc-framework-inputmethodkit",
    "pyobjc-framework-mediaextension",
    "pyobjc-framework-fskit",
    "mlx-metal",
}

# Keep responses for one hour
SESSION = requests_cache.CachedSession("requests-cache", expire_after=60 * 60)


def get_json_url(package_name):
    return BASE_URL + "/" + package_name + "/json"


def normalize(package_name: str) -> str:
    """Normalise a package name for a simple index URL.

    https://packaging.python.org/en/latest/specifications/name-normalization/
    """
    return re.sub(r"[-_.]+", "-", package_name).lower()


def in_rise_registry(package_name: str) -> bool:
    """Whether the RISE riscv64 registry has wheels for this package."""
    url = f"{RISE_REGISTRY_URL}/{normalize(package_name)}/"
    try:
        response = SESSION.get(url, allow_redirects=False)
    except Exception as e:
        print(f" ! Could not check the RISE registry for {package_name}: {e}")
        return False

    return response.status_code == 200


def annotate_wheels(packages, to_chart: int) -> list[dict]:
    print("Getting wheel data...")
    num_packages = len(packages)
    total = 0
    keep = []
    for index, package in enumerate(packages):
        print(f"{total + 1}/{to_chart} {index + 1}/{num_packages} {package['name']}")
        if package["name"] in DEPRECATED_PACKAGES | IGNORED_PACKAGES:
            continue

        has_other_binary_wheel = False
        has_riscv64_wheel = False
        has_pure_python_wheel = False
        in_registry = False
        url = get_json_url(package["name"])
        response = SESSION.get(url)
        if response.status_code != 200:
            print(" ! Skipping " + package["name"])
            continue

        data = response.json()

        for download in data["urls"]:
            if download["packagetype"] == "bdist_wheel":
                # The wheel filename is:
                # {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
                # https://packaging.python.org/en/latest/specifications/binary-distribution-format/#file-name-convention
                platform_tag = download["filename"].removesuffix(".whl").split("-")[-1]

                # A wheel may be tagged for several platforms at once, for
                # example manylinux_2_39_riscv64.musllinux_1_2_riscv64
                if "riscv64" in platform_tag:
                    has_riscv64_wheel = True
                elif platform_tag != "any":
                    has_other_binary_wheel = True
                else:
                    has_pure_python_wheel = True

        if has_riscv64_wheel:
            package["css_class"] = "success"
            package["icon"] = "\u2713"  # Check mark
        elif has_other_binary_wheel:
            in_registry = in_rise_registry(package["name"])
            if in_registry:
                package["css_class"] = "rise"
                package["icon"] = "📦"
            elif has_pure_python_wheel:
                package["css_class"] = "pure-py"
                package["icon"] = "🐍"
            else:
                package["css_class"] = "warning"
                package["icon"] = "\u2717"  # Ballot X
        else:
            # Don't show packages with only sdists or pure Python wheels
            continue

        package["riscv64_wheel"] = has_riscv64_wheel
        package["rise_registry"] = in_registry

        keep.append(package)
        total += 1
        if total == to_chart:
            break

    return keep


def get_top_packages():
    print("Getting packages...")

    with open("top-pypi-packages.json") as data_file:
        packages = json.load(data_file)["rows"]

    # Rename keys
    for package in packages:
        package["downloads"] = package.pop("download_count")
        package["name"] = package.pop("project")

    return packages


def save_to_file(packages, file_name):
    now = dt.datetime.now(tz=dt.timezone.utc)
    with open(file_name, "w") as f:
        f.write(
            json.dumps(
                {
                    "data": packages,
                    "last_update": now.strftime("%A, %d %B %Y, %X %Z"),
                },
                indent=1,
            )
        )
