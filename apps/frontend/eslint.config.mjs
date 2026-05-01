import eslintConfigNext from "eslint-config-next";

const eslintConfig = [
  ...eslintConfigNext,
  {
    rules: {
      "react-hooks/exhaustive-deps": "warn",
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/set-state-in-effect": "off",
    },
  },
];

export default eslintConfig;
