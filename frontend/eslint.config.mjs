import js from "@eslint/js";
import eslintReact from "@eslint-react/eslint-plugin";
import nextPlugin from "@next/eslint-plugin-next";
import { defineConfig, globalIgnores } from "eslint/config";
import jsxA11y from "eslint-plugin-jsx-a11y-x";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

const ignores = globalIgnores([
  ".next/**",
  "artifacts/**",
  "coverage/**",
  "node_modules/**",
  "playwright-report/**",
  "test-results/**",
]);

const javascript = {
  name: "rupturelab/javascript",
  files: ["**/*.{js,mjs,cjs}"],
  extends: [js.configs.recommended],
  languageOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
    globals: globals.nodeBuiltin,
  },
};

const typescript = {
  name: "rupturelab/typescript-react",
  files: ["**/*.{ts,tsx}"],
  extends: [
    js.configs.recommended,
    tseslint.configs.strict,
    eslintReact.configs["recommended-typescript"],
    reactHooks.configs.flat.recommended,
    jsxA11y.configs.recommended,
  ],
  plugins: {
    "@next/next": nextPlugin,
  },
  languageOptions: {
    globals: {
      ...globals.browser,
      ...globals.nodeBuiltin,
    },
  },
  rules: {
    ...nextPlugin.configs.recommended.rules,
    ...nextPlugin.configs["core-web-vitals"].rules,
    "no-undef": "off",
    "@typescript-eslint/no-unused-vars": [
      "error",
      {
        argsIgnorePattern: "^_",
        caughtErrorsIgnorePattern: "^_",
        varsIgnorePattern: "^_",
      },
    ],
  },
};

export default defineConfig([ignores, javascript, typescript]);
