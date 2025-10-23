# @prep/tsconfig

This package provides the shared TypeScript configuration for Prep services and packages.

## Usage

1. Add the workspace dependency to your package's `package.json`:

   ```json
   {
     "devDependencies": {
       "@prep/tsconfig": "workspace:*"
     }
   }
   ```

2. Extend the shared base config in your `tsconfig.json`:

   ```json
   {
     "extends": "@prep/tsconfig/tsconfig.base.json",
     "compilerOptions": {
       // package-specific overrides
     }
   }
   ```

Keeping all projects pointed to the shared config helps ensure a consistent TypeScript toolchain across the monorepo.
