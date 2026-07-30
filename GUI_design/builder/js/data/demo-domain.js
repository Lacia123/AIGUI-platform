/**
 * Domain 教学页示例 —— 使用「Domain 页式」组件容器预设 + 列布局包一层标题。
 */
export const DOMAIN_DEMO = {
  version: 1,
  children: [
    {
      kind: "container",
      type: "layout-column",
      width: "1/1",
      layout: "column",
      style: "plain",
      chrome: "hide",
      children: [
        {
          kind: "component",
          type: "heading",
          span: "full",
          props: { text: "The Domain", level: 1, accentWord: "Domain" },
        },
        {
          kind: "component",
          type: "text",
          span: "full",
          props: {
            text: "Think of it as the Guest List for your function. Only the values on this list are allowed in.",
          },
        },
        {
          kind: "container",
          type: "preset-domain",
          width: "1/1",
          layout: "grid",
          cols: "2",
          style: "plain",
          chrome: "hide",
          children: [
            {
              kind: "container",
              type: "slot-cell",
              width: "1/1",
              layout: "column",
              style: "soft",
              span: "1",
              chrome: "hide",
              children: [
                {
                  kind: "component",
                  type: "label",
                  props: { text: "CORE DEFINITION" },
                },
                {
                  kind: "component",
                  type: "definition",
                  props: {
                    body: 'The complete set of all possible <u>input values</u> for a function.',
                    footnote: "Also known as the 'Independent Variables'.",
                  },
                },
              ],
            },
            {
              kind: "container",
              type: "slot-cell",
              width: "1/1",
              layout: "column",
              style: "bordered",
              span: "1",
              chrome: "hide",
              children: [
                {
                  kind: "component",
                  type: "chart-line",
                  props: {
                    title: "Visualizing Domain: f(x) = √x",
                    caption: "Allowed Inputs (Domain): [0, +∞)",
                  },
                },
              ],
            },
            {
              kind: "container",
              type: "slot-cell",
              width: "1/1",
              layout: "row",
              style: "gradient",
              span: "full",
              chrome: "hide",
              children: [
                {
                  kind: "component",
                  type: "callout",
                  props: {
                    title: "The Input-Output Rule",
                    body: "Every allowed input from the domain maps to exactly one output in the range.",
                  },
                },
                {
                  kind: "component",
                  type: "image",
                  props: { caption: "Concept art" },
                },
              ],
            },
          ],
        },
      ],
    },
  ],
};
