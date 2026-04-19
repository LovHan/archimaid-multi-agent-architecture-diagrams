"""把 .drawio 文件导出为 PNG

支持三种后端 (按优先级):
1. 本地 drawio-desktop 二进制 (macOS: /Applications/draw.io.app/Contents/MacOS/draw.io)
2. docker rlespinasse/drawio-desktop-headless (跨平台 CI 友好)
3. 不可用时抛 RuntimeError, agent 会 warn 并跳过 PNG

用法:
    PngExporter().export("out.drawio", "out.png")
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

MACOS_DRAWIO_PATH = "/Applications/draw.io.app/Contents/MacOS/draw.io"
LINUX_DRAWIO_CANDIDATES = [
    "/usr/bin/drawio",
    "/usr/local/bin/drawio",
    "/snap/bin/drawio",
]


class PngExporter:
    def __init__(
        self,
        docker_image: str | None = None,
        scale: int = 2,
        border: int = 20,
        prefer: str = "auto",
    ) -> None:
        """
        prefer:
          - 'auto': 先本地二进制, 再 docker
          - 'local': 强制本地
          - 'docker': 强制 docker
        """
        self.docker_image = docker_image or os.getenv(
            "DRAWIO_DOCKER_IMAGE",
            "rlespinasse/drawio-desktop-headless:latest",
        )
        self.scale = scale
        self.border = border
        self.prefer = prefer

    # ---------- detection ----------

    @staticmethod
    def find_local_drawio() -> str | None:
        """返回本地 drawio 二进制路径, 若没找到返回 None"""
        if Path(MACOS_DRAWIO_PATH).exists():
            return MACOS_DRAWIO_PATH
        which = shutil.which("drawio")
        if which:
            return which
        for c in LINUX_DRAWIO_CANDIDATES:
            if Path(c).exists():
                return c
        return None

    @staticmethod
    def has_docker() -> bool:
        return shutil.which("docker") is not None

    def available(self) -> tuple[bool, str]:
        """检测是否可用, 返回 (available, method_or_reason)"""
        if self.prefer in ("auto", "local"):
            if (local := self.find_local_drawio()):
                return True, f"local:{local}"
            if self.prefer == "local":
                return False, "local drawio not found"
        if self.prefer in ("auto", "docker") and self.has_docker():
            return True, f"docker:{self.docker_image}"
        return False, "no available backend"

    # ---------- export ----------

    def export(
        self,
        drawio_path: str | Path,
        output_png: str | Path | None = None,
    ) -> Path:
        drawio_file = Path(drawio_path).resolve()
        if not drawio_file.exists():
            raise FileNotFoundError(drawio_file)

        if output_png is None:
            output_png = drawio_file.with_suffix(".png")
        output_png = Path(output_png).resolve()

        ok, method = self.available()
        if not ok:
            raise RuntimeError(
                f"PNG 导出后端不可用 ({method})。请:\n"
                f"  - macOS: 安装 https://www.drawio.com/\n"
                f"  - 或: docker pull {self.docker_image}"
            )

        if method.startswith("local:"):
            return self._export_via_local(
                method.split(":", 1)[1], drawio_file, output_png
            )
        else:
            return self._export_via_docker(drawio_file, output_png)

    def _export_via_local(
        self, binary: str, drawio_file: Path, output_png: Path
    ) -> Path:
        cmd = [
            binary,
            "--export",
            "--format",
            "png",
            "--scale",
            str(self.scale),
            "--border",
            str(self.border),
            "--output",
            str(output_png),
            str(drawio_file),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0 or not output_png.exists():
            raise RuntimeError(
                f"本地 drawio 导出失败: {result.stderr or result.stdout}"
            )
        return output_png

    def _export_via_docker(
        self, drawio_file: Path, output_png: Path
    ) -> Path:
        workdir = drawio_file.parent
        relative_in = drawio_file.name
        relative_out = output_png.name

        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{workdir}:/data",
            "-w",
            "/data",
            self.docker_image,
            "-x",
            "-f",
            "png",
            "--scale",
            str(self.scale),
            "--border",
            str(self.border),
            "-o",
            relative_out,
            relative_in,
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"drawio docker 导出失败 (exit={result.returncode}):\n"
                f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            )
        if not output_png.exists():
            raise RuntimeError(
                f"docker 成功但找不到文件 {output_png}\nstdout: {result.stdout}"
            )
        return output_png
