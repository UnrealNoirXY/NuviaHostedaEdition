# Frontend Build & Deployment Notes

This project uses the Vite build tool with Yarn classic (1.x). Follow the
instructions below to install the dependencies and compile the production
bundle without running into the most common errors we have observed during
server deployments.

## Prerequisites

* **Node.js 18 or newer** (Node 20 LTS is recommended).
* **Yarn 1.x** (`npm install -g yarn` if needed).
* The operating system user that runs the build must have write permissions on
  the repository directory (especially on `frontend/dist/`).

## Installing dependencies

From inside the `frontend/` directory run:

```bash
yarn install
```

> **Tip:** If you prefer NPM use `npm install` without any extra package name.
> Running `npm install frontend` tries to fetch a package called `frontend` from
> the public registry and pulls in legacy dependencies such as `node-sass`,
> which fails to compile on modern Node.js versions.

## Building for production

```bash
yarn build
```

The build output is written to `frontend/dist/`, which is later served by the
Django application from `/vite/`.

## Development server & HMR

With `DEBUG=True` Django now proxies asset requests to the Vite dev server. To
enable hot-module replacement start both processes when working locally:

```bash
# Terminal 1
yarn dev

# Terminal 2
python manage.py runserver
```

When `DEBUG=False` Django falls back to the manifest in `frontend/dist/.vite/`,
so production deploys are not affected by the dev server being offline.

## Troubleshooting

### `node-sass` build failures during `npm install`

If you mistakenly executed `npm install frontend` and now the installation is
broken, remove the extra `node_modules/` folder and lock file created by that
command:

```bash
rm -rf node_modules package-lock.json
npm install
```

Switch back to Yarn afterwards with `yarn install` to regenerate
`yarn.lock`.

### Permission denied writing `dist/sw.js`

When `yarn build` fails with:

```
Error: Unable to write the service worker file. 'EACCES: permission denied,
open '.../frontend/dist/sw.js''
```

it means the current user cannot modify the `frontend/dist/` directory. Fix the
ownership before running the build:

```bash
sudo chown -R $USER:$USER frontend/dist frontend
```

Alternatively, delete the folder as a privileged user (`sudo rm -rf
frontend/dist`) and run the build again; Vite will recreate it with the correct
permissions.

