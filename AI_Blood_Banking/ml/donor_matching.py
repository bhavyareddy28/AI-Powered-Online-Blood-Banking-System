# Smart Donor Matching System

from datetime import date, datetime


def is_donor_eligible(donor):
    """
    Check whether a donor is eligible based on last donation date.

    Donors who donated within the last 90 days
    are considered temporarily ineligible.
    """

    last_donation = donor.get("last_donation_date")

    # No previous donation date
    if not last_donation:
        return True

    # Convert string date to date object if necessary
    if isinstance(last_donation, str):
        last_donation = datetime.strptime(
            last_donation,
            "%Y-%m-%d"
        ).date()

    days_since_donation = (
        date.today() - last_donation
    ).days

    return days_since_donation >= 90


def calculate_match_score(
    donor,
    requested_blood_group,
    requested_city
):
    """
    Calculate a matching score for a donor.

    Maximum score = 100
    """

    # Check donation eligibility first
    if not is_donor_eligible(donor):
        return 0

    score = 0

    # Blood group match
    if donor["blood_group"].strip().upper() == requested_blood_group.strip().upper():
        score += 60
    else:
        return 0

    # City match
    if donor["city"].strip().lower() == requested_city.strip().lower():
        score += 30

    # Donor availability
    if donor.get("available", False):
        score += 10

    return score


def rank_donors(
    donors,
    requested_blood_group,
    requested_city
):
    """
    Rank only compatible and eligible donors.
    """

    ranked_donors = []

    for donor in donors:

        score = calculate_match_score(
            donor,
            requested_blood_group,
            requested_city
        )

        if score > 0:

            donor_copy = donor.copy()

            donor_copy["match_score"] = score

            ranked_donors.append(donor_copy)

    # Highest score first
    ranked_donors.sort(
        key=lambda donor: donor["match_score"],
        reverse=True
    )

    return ranked_donors


# Test the matching system
if __name__ == "__main__":

    donors = [
        {
            "name": "Donor 1",
            "blood_group": "A+",
            "city": "Hyderabad",
            "available": True,
            "last_donation_date": None
        },
        {
            "name": "Donor 2",
            "blood_group": "A+",
            "city": "Warangal",
            "available": True,
            "last_donation_date": None
        },
        {
            "name": "Donor 3",
            "blood_group": "B+",
            "city": "Hyderabad",
            "available": True,
            "last_donation_date": None
        }
    ]

    requested_blood_group = "A+"
    requested_city = "Hyderabad"

    matched_donors = rank_donors(
        donors,
        requested_blood_group,
        requested_city
    )

    print("\nSmart Donor Matching Results:")
    print("--------------------------------")

    for donor in matched_donors:

        print(
            donor["name"],
            "->",
            donor["match_score"],
            "%"
        )