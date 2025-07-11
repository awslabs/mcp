import React from 'react';
import Layout from '@theme/Layout';
import ServerCards from '@site/src/components/ServerCards';

export default function Servers(): React.ReactNode {
  return (
    <Layout
      title="AWS MCP Servers"
      description="Browse all available AWS MCP Servers">
      <main className="container margin-vert--lg">
        <h1 className="text--center margin-bottom--lg">Available MCP Servers</h1>
        <p className="text--center margin-bottom--xl">
          Browse all available AWS MCP Servers. Use the filters and search to find the servers you need.
        </p>
        <ServerCards />
      </main>
    </Layout>
  );
}
