Feature: All HTTP endpoints require authenticated callers
  Tied to design_docs/secure-endpoints.md.

  @secure-endpoints--auth-required
  Scenario: An unauthenticated request is rejected
    Given the application is running
    When a client makes a GET request to "/users/42" without a session token
    Then the response status is 401

  @secure-endpoints--auth-required
  Scenario: An authenticated request reaches the handler with caller identity
    Given the application is running
    And a user "andrew" has a valid session token "tok-abc"
    When a client makes a GET request to "/users/42" with token "tok-abc"
    Then the response status is 200
    And the handler observed request.user equal to "andrew"

  @secure-endpoints--auth-required
  Scenario: A request with an invalid token is rejected
    Given the application is running
    When a client makes a GET request to "/orders/7" with token "not-a-real-token"
    Then the response status is 401
