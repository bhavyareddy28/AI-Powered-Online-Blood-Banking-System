# -----------------------------
# Notification System
# -----------------------------

def create_notification_message(
    donor_name,
    blood_group,
    city
):
    message = (
        f"Hello {donor_name}, "
        f"there is a blood requirement for {blood_group} "
        f"in {city}. Please consider donating blood."
    )

    return message