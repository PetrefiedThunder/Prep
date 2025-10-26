import next from "eslint-config-next";
import jsxA11y from "eslint-plugin-jsx-a11y";
import testingLibrary from "eslint-plugin-testing-library";

export default [
  ...next,
  {
    plugins: {
      "jsx-a11y": jsxA11y,
      "testing-library": testingLibrary
    },
    rules: {
      "jsx-a11y/anchor-is-valid": "warn"
    }
  }
];
