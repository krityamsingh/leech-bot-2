FROM mysterysd/wzmlx:v3

WORKDIR /usr/src/app

# ── PHP + MadelineProto bridge ────────────────────────────────────────────────
# Installs PHP 8.2 + composer + AMPHP/MadelineProto deps so the optional
# php-bridge microservice can run alongside the Python bot in the same
# container. Disabled by default — toggle USE_PHP_TRANSPORT=True in config.py
# and run `php php-bridge/login.php` once to populate the session.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg lsb-release supervisor \
    && curl -sSL https://packages.sury.org/php/apt.gpg \
        -o /etc/apt/trusted.gpg.d/php.gpg \
    && echo "deb https://packages.sury.org/php/ $(lsb_release -sc) main" \
        > /etc/apt/sources.list.d/php.list \
    && apt-get update && apt-get install -y --no-install-recommends \
        php8.2-cli php8.2-mbstring php8.2-xml php8.2-curl \
        php8.2-gmp php8.2-zip php8.2-intl php8.2-bcmath \
        php8.2-readline php8.2-opcache \
    && curl -sS https://getcomposer.org/installer | php -- \
        --install-dir=/usr/local/bin --filename=composer \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN uv pip install --python /wzvenv/bin/python --no-cache-dir -r requirements.txt

# Code
COPY . .

# Install PHP deps inside php-bridge/
RUN if [ -f /usr/src/app/php-bridge/composer.json ]; then \
        cd /usr/src/app/php-bridge && \
        composer install --no-dev --no-interaction --prefer-dist --optimize-autoloader; \
    fi

RUN mkdir -p /usr/src/app/downloads /usr/src/app/php-bridge/data

ENTRYPOINT ["bash", "start.sh"]
