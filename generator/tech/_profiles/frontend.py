"""Frontend TechProfile entries."""

from typing import List

from generator.tech.profile import TechProfile

FRONTEND: List[TechProfile] = [
    TechProfile(
        name="reflex",
        display_name="Reflex",
        category="frontend",
        skill_name="reflex-framework",
        packages=["reflex"],
        readme_keywords=["reflex", "rxconfig"],
        detection_files=["rxconfig.py"],
        tools=["reflex"],
        rules={
            "high": [
                "Define all UI state in rx.State subclasses — never mutate state outside event handlers",
                "Use rx.var for computed properties; never call Python functions directly in component trees",
                "Run `reflex init` before `reflex run` — the .web/ directory is auto-generated, never edit it",
            ],
            "medium": [
                "Split large pages into component functions in separate files under components/",
                "Use rx.background for long-running async tasks to avoid blocking the event loop",
                "Store secrets in environment variables, not in rx.State or rxconfig.py",
            ],
        },
    ),
    TechProfile(
        name="react",
        display_name="React",
        category="frontend",
        skill_name="react-components",
        packages=["react"],
        readme_keywords=["react", "reactjs", "react.js"],
        tools=["npm", "webpack", "jest", "eslint"],
        rules={
            "high": [
                "Use functional components with hooks (not class components)",
                "Keep components pure - avoid side effects in render",
                "Use useCallback/useMemo for expensive computations",
                "Avoid prop drilling - use Context or state management",
            ],
            "medium": [
                "Split large components into smaller, reusable ones",
                "Use custom hooks to extract reusable logic",
                "Implement error boundaries for graceful failures",
                "Use React.lazy() for code splitting",
            ],
            "low": [
                "Add PropTypes or TypeScript for type safety",
                "Use React DevTools for debugging",
            ],
        },
    ),
    TechProfile(
        name="vue",
        display_name="Vue",
        category="frontend",
        skill_name="vue-components",
        packages=["vue"],
        readme_keywords=["vue", "vuejs", "vue.js"],
        tools=["npm", "vue-cli", "jest"],
    ),
    TechProfile(
        name="nextjs",
        display_name="Next.js",
        category="frontend",
        skill_name="",
        packages=["next"],
        readme_keywords=["next.js", "nextjs"],
        detection_files=["next.config.js", "next.config.ts", "next.config.mjs"],
    ),
    TechProfile(
        name="tailwindcss",
        display_name="TailwindCSS",
        category="frontend",
        skill_name="",
        packages=["tailwindcss"],
        readme_keywords=["tailwind", "tailwindcss"],
        detection_files=["tailwind.config.js", "tailwind.config.ts", "tailwind.config.mjs"],
    ),
    TechProfile(
        name="vite",
        display_name="Vite",
        category="frontend",
        skill_name="",
        packages=["vite"],
        readme_keywords=["vite"],
        detection_files=["vite.config.js", "vite.config.ts", "vite.config.mjs"],
    ),
    TechProfile(
        name="konva",
        display_name="Konva",
        category="frontend",
        skill_name="konva-nesting-canvas",
        packages=["konva"],
        readme_keywords=["konva", "konvajs", "konva.js"],
    ),
    TechProfile(
        name="canvas",
        display_name="Canvas",
        category="frontend",
        skill_name="konva-nesting-canvas",
        packages=[],
        readme_keywords=["canvas", "svg canvas", "html canvas"],
    ),
    TechProfile(
        name="threejs",
        display_name="Three.js",
        category="frontend",
        skill_name="threejs-scene",
        packages=[],
        readme_keywords=["three.js", "threejs", "three js", "webgl", "3d extrusion"],
    ),
    TechProfile(
        name="babylon",
        display_name="Babylon.js",
        category="frontend",
        skill_name="babylon-scene",
        packages=[],
        readme_keywords=["babylon", "babylonjs", "babylon.js"],
    ),
    TechProfile(
        name="chrome",
        display_name="Chrome Extension",
        category="frontend",
        skill_name="chrome-extension",
        packages=[],
        readme_keywords=["chrome", "chrome extension", "manifest.json"],
    ),
]
