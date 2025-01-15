FROM python:3.13-slim-bookworm

RUN apt-get update

# Set correct timezone
RUN ln -sf /usr/share/zoneinfo/America/Los_Angeles /etc/localtime

# Create generic batchcd user
RUN useradd -c "generic app user" -d /home/batchcd -s /bin/bash -m batchcd

# Switch to application directory, creating it if needed
WORKDIR /home/batchcd/process_files

# Make sure batchcd owns app directory, if WORKDIR created it:
# https://github.com/docker/docs/issues/13574
RUN chown -R batchcd:batchcd /home/batchcd

# Change context to batchcd user for remaining steps
USER batchcd

# Copy application files to image, and ensure batchcd user owns everything
COPY --chown=batchcd:batchcd . .

# Include local python bin into batchcd user's path, mostly for pip
ENV PATH /home/batchcd/.local/bin:${PATH}

# Make sure pip is up to date, and don't complain if it isn't yet
RUN pip install --upgrade pip --disable-pip-version-check

# Install requirements for this application
RUN pip install --no-cache-dir -r requirements.txt --user --no-warn-script-location
