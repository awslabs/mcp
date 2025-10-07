import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const config: Config = {
  title: 'AWS MCP Servers',
  tagline: 'Get started with AWS MCP Servers and learn core features',
  favicon: 'img/aws-logo.svg',
  trailingSlash: false,

  // Future flags, see https://docusaurus.io/docs/api/docusaurus-config#future
  future: {
    v4: true, // Improve compatibility with the upcoming Docusaurus v4
  },

  // Set the production url of your site here
  url: 'https://awslabs.github.io',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/mcp/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'awslabs', // Usually your GitHub org/user name.
  projectName: 'mcp', // Usually your repo name.

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'throw',

  // Add plugins
  plugins: [],

  // Add scripts to be loaded in the client
  scripts: [],

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl:
            'https://github.com/awslabs/mcp/tree/main/',
          routeBasePath: '/', // Serve docs at the site's root
          remarkPlugins: [],
          rehypePlugins: [],
        },
        theme: {
          customCss: ['./src/css/custom.css', './src/css/doc-override.css'],
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    // Replace with your project's social card
    colorMode: {
      defaultMode: 'light',
      disableSwitch: true,
    },
    image: 'img/aws-logo.svg',
    navbar: {
      title: 'AWS MCP Servers',
      logo: {
        alt: 'AWS MCP Servers Logo',
        src: 'img/aws-logo.svg',
      },
      items: [
        {
          href: 'https://github.com/awslabs/mcp',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Documentation',
          items: [
            {
              label: 'Get Started',
              to: '/',
            },
            {
              label: 'Installation',
              to: '/installation',
            },
          ],
        },
        {
          title: 'Resources',
          items: [
            {
              label: 'AWS Blog',
              href: 'https://aws.amazon.com/blogs/machine-learning/introducing-aws-mcp-servers-for-code-assistants-part-1/',
            },
            {
              label: 'Model Context Protocol',
              href: 'https://modelcontextprotocol.io/introduction',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/awslabs/mcp',
            },
          ],
        },
      ],
      copyright: `© Amazon Web Services, Inc. or its affiliates. All rights reserved.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
