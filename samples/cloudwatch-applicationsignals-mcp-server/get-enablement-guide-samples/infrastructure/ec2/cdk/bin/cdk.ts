#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { EC2AppStack, AppConfig } from '../lib/cdk-stack';
import * as fs from 'fs';
import * as path from 'path';

const app = new cdk.App();

// Use account/region from environment or CLI config
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

// Read all config files from config directory
const configDir = fs.realpathSync(path.resolve(__dirname, '../config'));
const configFiles = fs.readdirSync(configDir).filter(f => f.endsWith('.json'));

// Create a stack for each config
configFiles.forEach(configFile => {
  const sanitizedName = path.basename(configFile);

  if (sanitizedName.includes('..') || sanitizedName.includes(path.sep)) {
    throw new Error(`Invalid config file name: ${configFile}`);
  }

  const configPath = path.join(configDir, sanitizedName);

  const realConfigPath = fs.realpathSync(configPath);
  if (!realConfigPath.startsWith(configDir + path.sep)) {
    throw new Error(`Path traversal detected: ${configFile}`);
  }

  const config: AppConfig = JSON.parse(fs.readFileSync(realConfigPath, 'utf-8'));

  const stackId = `${config.appName}Stack`;

  new EC2AppStack(app, stackId, config, { env });
});

app.synth();
